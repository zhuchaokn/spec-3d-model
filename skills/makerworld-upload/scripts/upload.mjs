import fs from 'node:fs/promises';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {createHash} from 'node:crypto';

const TAG_FIELD = '按 "Enter "键来分隔标签。从下拉列表中选择类似的标签，以便更好地搜索。';
const EDITOR = 'Editor editing area: main. Press ⌥0 for help.';

/** Works with the documented Codex Tab API or a standalone Playwright Page adapter. */
export async function uploadDraft(tab, manifest, {checkpoint, screenshotPath} = {}) {
  const ui = tab.playwright;
  const model = manifest.model;
  if (!model?.file || !model.title || !model.description || !model.category)
    throw new Error('Missing model.file/title/description/category');
  if (manifest.mode && manifest.mode !== 'draft')
    throw new Error('This adapter saves drafts. Publishing needs a verified print-profile adapter.');
  const site = manifest.site || 'https://makerworld.com.cn';
  if (!['https://makerworld.com.cn', 'https://makerworld.com'].includes(site))
    throw new Error('Unsupported MakerWorld site');
  if (manifest.draft_url && !manifest.draft_url.startsWith(`${site}/zh/my/models/drafts/`))
    throw new Error('draft_url must point to this site’s model draft');
  const dest = manifest.draft_url || `${site}/zh/my/models/publish?type=original`;
  if (await tab.url() !== dest) await tab.goto(dest);
  const initial = await ui.domSnapshot();
  if (/登录 \/ 注册|Log in|Sign in/.test(initial) && !initial.includes('Bambu Studio'))
    throw new Error('LOGIN_REQUIRED: sign in in this browser, then resume with the same manifest.');

  async function file(button, filename) {
    const pending = ui.waitForEvent('filechooser', {timeoutMs: 10000});
    await button.click();
    const chooser = await pending;
    await chooser.setFiles(filename);
  }
  if (!manifest.draft_url) {
    await ui.getByRole('radio', {name: '是（赚取额外积分奖励）', exact: true}).check();
    await ui.getByRole('button', {name: '下一步', exact: true}).click();
    await file(ui.getByRole('button', {name: '浏览', exact: true}).first(), model.file);
    await ui.getByRole('button', {name: '下一步', exact: true}).waitFor({state: 'visible'});
    // Click waits for upload completion/enabled state in Playwright.
    await ui.getByRole('button', {name: '下一步', exact: true}).click({timeoutMs: 60000});
    await ui.getByRole('textbox', {name: EDITOR, exact: true}).waitFor({state: 'visible', timeoutMs: 60000});
    const created = await tab.url();
    if (!/\/my\/models\/drafts\/\d+\/edit/.test(created))
      throw new Error('Draft URL missing after upload; inspect before retrying creation.');
    manifest.draft_url = created;
    if (checkpoint) await checkpoint(manifest); // Record ID before any further changes.
  }

  await ui.getByRole('textbox').nth(1).fill(model.title);
  await ui.getByRole('textbox', {name: EDITOR, exact: true}).fill(model.description);
  // Clearing first triggers the search even when resuming the same selected category.
  await ui.getByRole('combobox', {name: '输入类别关键字快速搜索', exact: true}).fill('');
  await ui.getByRole('combobox', {name: '输入类别关键字快速搜索', exact: true}).fill(model.category);
  await ui.getByRole('option', {name: model.category, exact: true}).click();
  // Existing tag chips are left in place; Enter skips tags already present in the editor.
  for (const tag of model.tags || []) {
    await ui.getByRole('combobox', {name: TAG_FIELD, exact: true}).fill(tag);
    await ui.getByRole('combobox', {name: TAG_FIELD, exact: true}).press('Enter');
  }
  // Upload photos only once; record progress immediately to make resumes idempotent.
  const media = manifest.uploaded_media ||= [];
  for (const photo of model.photos || []) {
    if (media.includes(photo)) continue;
    await file(ui.getByRole('button', {name: '添加照片', exact: true}).first(), photo);
    await ui.getByRole('button', {name: '保存草稿', exact: true}).click({timeoutMs: 60000});
    media.push(photo);
    if (checkpoint) await checkpoint(manifest);
  }
  if (model.cover && !manifest.cover_uploaded) {
    await file(ui.getByRole('button', {name: '4:3 封面', exact: true}), model.cover);
    await ui.getByRole('button', {name: '提交', exact: true}).click();
    await ui.getByRole('button', {name: '保存草稿', exact: true}).click({timeoutMs: 60000});
    manifest.cover_uploaded = true;
    if (checkpoint) await checkpoint(manifest);
  }
  // License/visibility are intentionally preserved; no agreement or publish action here.
  await ui.getByRole('button', {name: '保存草稿', exact: true}).click({timeoutMs: 60000});
  await tab.reload();
  await ui.getByRole('textbox', {name: EDITOR, exact: true}).waitFor({state: 'visible'});
  const saved = await ui.getByRole('textbox').nth(1).getAttribute('value');
  const description = await ui.getByRole('textbox', {name: EDITOR, exact: true}).textContent();
  if (saved !== model.title || !description?.includes(model.description.split('\n')[0]))
    throw new Error('SAVED_CONTENT_MISMATCH: keep this draft and inspect, do not create another.');
  const snapshot = await ui.domSnapshot();
  const result = {status: 'draft_saved', draft_url: manifest.draft_url,
    publication_status: 'not_published', screenshot: screenshotPath || null};
  if (screenshotPath) await fs.writeFile(screenshotPath, await tab.screenshot({fullPage: true}));
  if (checkpoint) await checkpoint(manifest);
  return {...result, snapshot};
}

export async function runFromManifest(tab, manifestPath, screenshotPath) {
  const manifest = JSON.parse(await fs.readFile(manifestPath, 'utf8'));
  for (const [filename, expected] of Object.entries(manifest.files_sha256 || {})) {
    const actual = createHash('sha256').update(await fs.readFile(filename)).digest('hex');
    if (actual !== expected) throw new Error(`FILE_CHANGED: ${filename}; regenerate the reviewed package.`);
  }
  const checkpoint = async value => {
    const temp = `${manifestPath}.tmp`;
    await fs.writeFile(temp, JSON.stringify(value, null, 2));
    await fs.rename(temp, manifestPath);
  };
  const result = await uploadDraft(tab, manifest, {checkpoint, screenshotPath});
  await fs.writeFile(`${manifestPath}.result.json`, JSON.stringify(result, null, 2));
  return result;
}

// Standalone mode uses a dedicated persistent browser profile, with one normal login.
async function main() {
  const args = process.argv.slice(2);
  const manifestPath = args[0];
  if (!manifestPath) throw new Error('Usage: node upload.mjs manifest.json [--login]');
  const manifest = JSON.parse(await fs.readFile(manifestPath, 'utf8'));
  const {chromium} = await import(process.env.MAKERWORLD_PLAYWRIGHT_MODULE || 'playwright');
  const profile = manifest.browser_profile || path.join(path.dirname(manifestPath), '.browser-profile');
  const context = await chromium.launchPersistentContext(profile, {headless: false});
  try {
    const page = context.pages()[0] || await context.newPage();
    if (args.includes('--login')) {
      await page.goto(manifest.site || 'https://makerworld.com.cn');
      console.log('Log in normally in this dedicated browser, then close it and rerun without --login.');
      await new Promise(resolve => context.on('close', resolve));
      return;
    }
    const tab = {playwright: Object.assign(Object.create(page), {
      domSnapshot: () => page.locator('body').innerText(),
    }), url: () => page.url(), goto: url => page.goto(url), reload: () => page.reload(),
      screenshot: options => page.screenshot({...options, type: 'jpeg'})};
    const result = await runFromManifest(tab, manifestPath, `${manifestPath}.jpg`);
    console.log(JSON.stringify({...result, snapshot: undefined}, null, 2));
  } finally {
    await context.close();
  }
}
if (typeof process !== 'undefined' && process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  main().catch(error => {console.error(error.message); process.exitCode = 1;});
}

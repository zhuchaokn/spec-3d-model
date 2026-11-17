# 3D 中国地图制作故事 / 导演版

用户确认的六段口播保持原样，Yunxi 男声 +18%。连续口播，无额外句间静音，总长 97.152 秒。9:16，一键自动配音、字幕与换页，结束可重播；无手动翻页控制栏。

镜头按 cinematic_plan.md 组织。地图约 0.38 秒迅速落平；口播进入 Z 高度时，约 0.6 秒完成拉升，之后才转低角度展示，最后切山脉横向近景。海洋根据真实掩膜在约 0.48 秒内扫入；灰色平台扣除海洋表面，海洋下方独立分层，不再铺设同高度重叠顶面。显示岸线保留 3 微米几何分隔以抵御坐标量化误差，打印文件不变。海洋材质保持不透明，镜头移向南海附图。插板抬起后，沿国境轮廓的临时显示填充层下沉 0.2 cm，插板再嵌入。拆件先分离省份，再展开四片底座。

影院显示模型来自原省份几何、底座源轮廓、真实海洋掩膜与完整岛礁纹理；显示底座按源轮廓分层轻量重建，不修改原 Blender 或打印文件。源数据需要在本项目中存在才能重建影院资产；仓库中的 cinema-mesh.js 与 cinema-inset.svg 是可直接使用的最终显示副本。

运行 package_story.py 生成 output/story_public 和完整离线 HTML ZIP。direct_story.py 恢复 voice_source 中的原男声，移除额外停顿并同步字幕与下载合并音轨；不重新调用语音服务。build_cinematic_assets.py 只构建显示资产。测试 tests/check_cinematic.cjs 接受 LitePage 包预览 URL，验证连续播放、重播、快速落平与 Z 拉升后转镜、凹槽下陷、四片拆分、排版与邻近相机位的海洋像素稳定性；tests/check_sea_geometry.py 验证最终导出网格的海陆顶面无重叠及口播原文不变；不会截图。

音频六段，共 391182 字节，24kHz 单声道 32kbps；每两段合并为三批下载。首页不请求音频或模型；点击后用约 380 KB 的连续音轨驱动六章镜头，切章不切换音源。六段及三批文件保留用于下载。点击播放后准备三维镜头；WebGL 无法使用时保留截图与二维过程示意。完整配音 narration.mp3，字幕 captions.srt。

公开链接：https://lightpage.hqdx.store/p/bpm5ij5c/

当前播放将上述动作基准时长统一乘以 1.2（120%），短距离运镜、数据流与转场同步放慢。动作触发点仍由原旁白对齐；音轨、字幕与整片 97.152 秒时间轴保持原样。

## 固定脚本：逐帧导出视频

在仓库根目录运行：

```bash
python3 projects/china_relief/story/export_video.py
```

默认生成 `projects/china_relief/output/video/china-map-story.mp4`、同名 `.cover.png` 封面和 `.export.json` 验证报告。格式为 1080 × 1920、30 fps、H.264 / AAC、yuv420p，保留原连续男声与烧录字幕。脚本直接读取本地故事源码；不需要打开浏览器或访问线上网页，不修改 Blender 和打印工程。

脚本先解码全部图片、字体与南海纹理，再按 `frame / fps` 求每帧状态，手动定位 SVG 数据流时间，并通过无损 PNG 管道交给 FFmpeg。浏览器加载时间与渲染速度不进入视频。界面转场在导出模式使用镜头切换，避免依赖浏览器墙钟的 CSS 渐变；场景动作和运镜仍沿用原时间轴。动画时长倍率保持 1.2。

导出前验证跨章节往返定位的一致性；GPU 对极少数边缘抗锯齿像素的 1–3 级舍入差异允许保留。完成后用 ffprobe 核验尺寸、帧数、音视频编码和时长，再将临时 MP4 改为正式文件。整个过程不保存数千张帧图，仅保留视频、封面与报告。

可选参数示例：

```bash
# 输出一个五秒预览，原旁白自动裁到相同时间段
python3 projects/china_relief/story/export_video.py --start 30 --duration 5 --output /tmp/map-preview.mp4
# 指定输出文件；已存在时显式覆盖
python3 projects/china_relief/story/export_video.py --output /tmp/china-map.mp4 --overwrite
# 较小尺寸的检查版
python3 projects/china_relief/story/export_video.py --width 720 --height 1280
```

依赖 Python 3、Node.js、FFmpeg、Playwright 与其 Chromium。脚本自动寻找本机 Codex 捆绑的 Node / Playwright 和 Playwright 浏览器缓存；普通环境可先安装 `npm install playwright`、`npx playwright install chromium` 和 FFmpeg。也可通过 `--node`、`--playwright`、`--chromium` 指定已有安装路径。不会自动安装或修改系统依赖。

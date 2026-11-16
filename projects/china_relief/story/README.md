# 3D 中国地图制作故事 / 导演版

用户确认的六段口播保持原样，Yunxi 男声 +18%。加入句间观看停顿，总长 119.882 秒。9:16，一键自动配音、字幕与换页，结束可重播；无手动翻页控制栏。

镜头按 cinematic_plan.md 组织。地形从俯视转低角度，约 10.5 秒升高，完成后观察并切山脉横向近景。海洋根据真实掩膜加入，镜头移向南海附图。插板抬起后，沿国境轮廓的临时显示填充层下沉 0.2 cm，插板再嵌入。拆件先分离省份，再展开四片底座。

影院显示模型来自原省份几何、底座源轮廓、真实海洋掩膜与完整岛礁纹理；显示底座按源轮廓分层轻量重建，不修改原 Blender 或打印文件。源数据需要在本项目中存在才能重建影院资产；仓库中的 cinema-mesh.js 与 cinema-inset.svg 是可直接使用的最终显示副本。

运行 package_story.py 生成 output/story_public 和完整离线 HTML ZIP。direct_story.py 根据 voice_source 中的原男声插入观看停顿并同步字幕；不重新调用语音服务。build_cinematic_assets.py 只构建显示资产。测试 tests/check_cinematic.cjs 接受 LitePage 包预览 URL，验证播放、运镜、凹槽下陷、四片拆分、排版与 GPU 实际绘制；不会截图。

音频六段，共 480366 字节，24kHz 单声道 32kbps；每两段合并为三批下载。首页不请求音频或模型，点击播放后准备三维镜头；WebGL 无法使用时保留截图与二维过程示意。完整配音 narration.mp3，字幕 captions.srt。

公开链接：https://lightpage.hqdx.store/p/bpm5ij5c/

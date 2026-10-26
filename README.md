# Aleafy Arch 软件仓库

将个人 fork 的功能保留在维护分支，由 GitHub Actions 构建并签名，再通过 GitHub Pages 向 pacman 发布。

| 软件包 | 源码仓库 | 维护分支 |
| --- | --- | --- |
| `linux-arctis-manager` | [Linux-Arctis-Manager](https://github.com/zhuceyezi/Linux-Arctis-Manager) | `main` |
| `elyterminal` | [ELYTerminal](https://github.com/zhuceyezi/ELYTerminal) | `linux-window-reuse` |

仓库还提供 Arctis Manager 所需的 `python-pulsectl`，固定在原项目的 24.12.0 发布提交。
该依赖不包含本地功能修改。其 epoch 保持为 1，与 CachyOS 的包兼容。

## 日常升级

本机完成一次接入后，运行：

```sh
sudo pacman -Syu
```

软件包名保持不变，pacman 直接管理程序、启动器、服务和资源文件。
用户设置仍保存在自己的配置目录中。构建和发布不会自动安装软件或重启应用。
Arctis Manager 优先沿用软件包提供的用户服务，图形界面不会额外生成文件遮住系统服务。
ELYTerminal 升级后，新启动的进程使用新程序；已经运行的窗口会继续使用原程序，关闭这些窗口后再启动即可。

## 发布自定义功能

在 `/home/aleafy/code/` 中维护 fork，验证后将修改提交并推送到表格中的维护分支。
GitHub Actions 每半小时检查一次源码提交和打包配方；有变化才构建，每七天也会重新构建以适配 Arch 的滚动依赖。
GitHub 的定时任务可能延迟。需要立即构建时，在本仓库的 Actions 页面运行 **Build and publish Arch repository**。
选中 `rebuild` 可以强制构建。

软件包版本为 `上游版本.r维护分支提交数.g提交缩写-构建编号`。
因此，增加自定义功能不必等上游发布新版本，pacman 也能识别升级。
本机定时任务每六小时检查正式上游版本，按 [上游维护流程](UPSTREAM.md) 自动合并并保留自定义功能。
先通过功能核对及 GitHub 候选构建，再更新维护分支并发布。遇到冲突或兼容性问题时停止并通知用户。
执行自动维护需要电脑开机、Codex 应用运行；构建与发布仍由 GitHub 完成。
请勿通过 force push 或重建分支降低发布版本；发布流程会拒绝降级。

## 发布和签名

构建使用干净的 Arch 容器，makepkg 以普通用户运行，源码固定到检查阶段确定的提交。
所有构建任务均成功后，独立发布任务才取得专用的 OpenPGP 签名密钥。
软件包和仓库数据库均要求受信任的签名，客户端不会关闭签名检查。
GitHub Pages 一次部署完整的数据库、签名和软件包，避免更新时客户端读到不一致的文件。

- pacman 地址：`https://zhuceyezi.github.io/arch-packages/x86_64`
- 公开密钥：`keyring/aleafy.asc`；指纹：`keyring/fingerprint`
- Actions secret：`REPO_SIGNING_KEY`，仅保存专用签名私钥
- Actions variable：`REPO_SIGNING_FINGERPRINT`，必须与仓库公开密钥一致
- `repo` Release 保存发布状态和软件包；其中的 `manifest.json` 记录源码提交、配方摘要和版本
- Pages 保留每个软件包最近三个版本，便于短期回退；历史 Release 资产不自动删除

私钥只应保存在本机专用密钥目录和 GitHub Actions secret，不能提交到 Git。
密钥有效期两年；到期前应延长有效期、更新公开密钥和 secret，并重新导入客户端密钥。
GitHub 公共仓库的定时任务可能因长期无活动停用；可在 Actions 页面重新启用。

## 接入另一台 Arch 电脑

下载本仓库，独立核对 `keyring/fingerprint` 与已信任设备上的值后运行：

```sh
pkexec bash scripts/install-system.sh
sudo pacman -Syu linux-arctis-manager elyterminal
```

接入脚本会备份 `/etc/pacman.conf` 到 `/var/backups/aleafy-arch/`，导入并本地信任公开密钥，
将独立配置 `/etc/pacman.d/aleafy.conf` 放在其他仓库之前。
仅使用当前仓库的已发布二进制文件，不在升级时以管理员身份编译源码。

## 回退与维护

旧软件包可从 `repo` Release 下载。核对签名后用 `sudo pacman -U 软件包文件` 回退。
如需暂时停用仓库，删除 `/etc/pacman.conf` 中的 `Include = /etc/pacman.d/aleafy.conf`。
现有已安装软件和个人设置会保留；如需彻底取消接入，可恢复 `/var/backups/aleafy-arch/` 中的配置备份。

构建失败会保留上一次已部署的完整仓库；修复源码或配方后重新运行工作流。
Arch/Python 更新主版本后，如尚未构建匹配的新包，应先在 Actions 中强制重新构建，再升级系统。

## 本地构建

按 PKGBUILD 安装构建依赖后，在对应的 `packages/软件名/` 目录运行 `makepkg`。
`SOURCE_COMMIT` 可固定源码提交，`PKGREL_OVERRIDE` 可设置构建编号。
ELYTerminal 编译要求至少 Rust 1.95；仓库使用 Arch 的系统 Rust，依赖固定在 `Cargo.lock`。

打包配方和发布工具按 MIT 许可证发布。软件包中各项目及其资源保留原许可证。

# Unity 角色资源获取指南

本仓库不包含 Mixamo 角色与动画文件（授权要求）。请按以下步骤自行获取，
放入 `client-unity/Assets/` 下对应目录即可（.meta 导入设置已随仓库提供）。

## 1. 角色模型

1. 访问 https://www.mixamo.com ，用 Adobe 账号登录；
2. 在 Characters 中任选一个喜欢的人形角色；
3. 点 Download，设置：**Format = FBX Binary**、**Pose = T-pose**、**Skin = With Skin**。

## 2. 动画

在 Animations 中搜索并分别下载 **Idle** 和 **Talking**：

- Format = FBX Binary
- Frames per Second = 30
- Keyframe Reduction = none
- Skin = **Without Skin**（动画不重复携带模型）

## 3. 导入 Unity

1. 将 FBX 放入 `client-unity/Assets/` 下对应目录，文件名与仓库中的 `.meta` 保持一致；
2. 选中角色，Animation Type 设为 **Humanoid** 并创建 Avatar；
3. 两段动画同样设为 Humanoid，关联角色的 Avatar；
4. 打开 `Main.unity`，确认 Idle / Talking 动画可正常播放。
# SnapByFace 开发指导指令


你现在负责开发 SnapByFace 项目。


首先阅读：

SNAPBYFACE_SPEC.md


严格按照产品规格开发。

文件处理边界：

- 项目只处理静态照片；
- 照片扫描支持常见相机 RAW 格式；
- 不实现视频文件导入、索引或播放；
- 摄像头视频流仅作为实时拍照搜索的采集源。


---

## 开发原则


不要一次生成全部代码。


采用：

模块化迭代开发。


每完成一个模块：

必须：

1. 创建代码
2. 创建测试
3. 说明设计
4. 等待下一步


---

# 第一阶段


初始化项目。


要求：

创建：

```
app/

ui/

services/

core/

repositories/

workers/

database/

tests/

```


实现：

- 配置系统
- 日志系统
- SQLite初始化


---

# 第二阶段


实现照片管理。


功能：

- 指定照片目录
- 扫描照片
- hash去重
- 数据库存储
- 增量扫描


---

# 第三阶段


实现实时照片监听。


要求：

- 文件变化检测
- 任务队列
- 后台Worker


---

# 第四阶段


实现AI Engine。


要求：

封装：


FaceEngine


接口：


```
detect()

embedding()

process()

```


不要把AI代码写入UI。


---

# 第五阶段


实现FAISS搜索。


接口：


```
add_vector()

search()

delete()

```


---

# 第六阶段


实现搜索页面。


流程：


USB Camera

↓

FaceEngine

↓

SearchService

↓

Result


---

# 第七阶段


实现授权系统。


要求：

- 机器码
- 试用15天
- 授权码
- 到期检查
- 防删除绕过


---

# 第八阶段


打包Windows。


要求：

PyInstaller。


生成：

安装包。


---

# 编码要求


语言：

Python。


GUI：

PyQt6。


数据库：

SQLite。


AI：

InsightFace。


向量：

FAISS。


代码要求：

- 类型提示
- 注释
- 单元测试
- 异常处理


---

# 禁止事项


禁止：

1. 把所有代码写在main.py。

2. UI直接调用数据库。

3. AI阻塞主线程。

4. 写死路径。

5. 写死参数。


---

# 每次开发前


先说明：

1. 修改哪些文件。

2. 为什么这样设计。

3. 如何测试。


然后开始编码。

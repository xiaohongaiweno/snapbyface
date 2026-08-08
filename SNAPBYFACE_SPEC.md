# SnapByFace 产品技术规格说明书

Version: 1.0


# 1. 产品定位


SnapByFace 是一款面向景区摄影行业的 AI 人脸检索系统。


使用场景：

摄影师固定位置拍摄游客照片。

照片自动传输到电脑。

游客回来购买照片。

工作人员通过 USB 摄像头采集游客人脸。

系统快速找到游客照片。


核心价值：

> 3秒找到游客刚刚拍摄的照片，提高照片销售效率。


---

# 2. 产品目标


解决：

传统方式：

摄影师拍摄大量照片。

工作人员打开文件夹人工查找。

照片数量越多，查找越困难。


SnapByFace：

游客拍脸。

AI搜索。

返回照片。

打印出售。


---

# 3. 系统形态


V1:

Windows桌面软件。


技术：

Python + PyQt6。


运行模式：

本地离线。


网络：

仅用于：

- 下载模型
- 激活授权


照片、人脸数据：

全部本地处理。


---

# 4. 总体架构


采用：

分层架构。


```
UI Layer

↓

ViewModel

↓

Service Layer

↓

Core Engine

↓

Repository

↓

SQLite + FAISS

```


---

# 5. 项目目录


```
snapbyface/

app/

ui/

viewmodels/

services/

core/

repositories/

database/

models/

workers/

utils/

resources/

tests/

logs/

```


---

# 6. 核心模块


## 6.1 Photo Service


负责：

- 图片扫描
- 新照片发现
- 文件管理
- 状态管理


---

## 6.2 Index Service


负责：

照片AI索引。


流程：


```
照片

↓

人脸检测

↓

特征提取

↓

FAISS

```


---

## 6.3 Search Service


负责：

游客搜索。


流程：


```
USB Camera

↓

Face Detection

↓

Embedding

↓

FAISS Search

↓

照片结果

```


---

## 6.4 License Service


负责：

授权。


---

# 7. AI设计


采用：


## 人脸检测

SCRFD


## 特征提取

ArcFace


输出：

512维Embedding。


## 向量搜索

FAISS


---

# 8. AI流程


```
Image

↓

SCRFD

↓

Face Alignment

↓

ArcFace

↓

512 Embedding

↓

FAISS

↓

Similarity

↓

Result

```


---

# 9. 相似度


采用：

Cosine Similarity。


显示：

例如：

```
相似度 92.6%
```


默认阈值：

80%。


管理员可以设置。


配置：

```
face.threshold
```


---

# 10. 实时照片处理


照片目录不断增加。


必须支持：

实时扫描。


流程：


```
Photo Folder

↓

Watcher

↓

Queue

↓

AI Worker

↓

FAISS Update

```


---

# 11. 不重复扫描


每张照片：

计算hash。


数据库保存。


再次扫描：

如果hash存在：

跳过。


---

# 12. 启动扫描


景区晚上关机。


所以：

不要定时重建。


启动软件时：

执行扫描。


流程：


```
启动

↓

扫描目录

↓

比较数据库

↓

发现新增照片

↓

加入任务队列

```


---

# 13. 索引状态


必须展示：


```
照片总数

已扫描

处理中

未完成

最后更新时间

```


目的：

区分：

没有照片

和

照片还没处理。


---

# 14. 数据库


使用：

SQLite。


表：

```
photo

face

face_embedding

scan_task

index_task

system_config

license

print_record

operation_log

```


---

# 15. Photo表


保存：

- 路径
- 文件名
- hash
- 文件大小
- 时间
- 状态
- 人脸数量


---

# 16. Face表


保存：

- photo_id
- 人脸框
- 质量评分


---

# 17. Embedding


向量：

不保存SQLite。


保存：

FAISS。


SQLite保存：

vector_id。


---

# 18. FAISS


V1:

IndexFlatIP


未来：

IVF


---

# 19. UI设计


页面：


```
首页

找片

索引状态

设置

授权

日志

```


---

# 20. 找片页面


核心页面。

输入边界：

- 照片目录只处理静态照片；
- 支持 JPEG、PNG、TIFF、BMP、WebP 以及常见相机 RAW 格式；
- 不处理视频文件；
- OpenCV `VideoCapture` 仅用于 USB 摄像头实时采集。


流程：


```
摄像头

↓

拍摄人脸

↓

搜索

↓

显示照片

↓

打印

```


结果显示：

```
照片

相似度

拍摄时间

```


---

# 21. 设置


包含：


## 照片目录


管理员指定。


例如：

```
D:/SnapPhotos
```


目录内部：

按照日期：

```
2026-08-02

2026-08-03

```


---

## 人脸参数


包含：

相似度阈值。


---

# 22. 授权系统


授权绑定：

机器码。


流程：


```
软件生成机器码

↓

用户官网购买

↓

生成授权码

↓

输入软件

↓

激活

```


---

# 23. 授权周期


支持：

- 15天试用
- 1个月
- 3个月
- 6个月
- 1年


---

# 24. 授权安全


防止删除授权绕过。


设计：

license.dat


保存：

多个位置。


验证：

- 机器码
- 签名
- 时间


---

# 25. 多线程


UI不能阻塞。


后台：


```
Scanner Worker

Index Worker

Search Worker

```


---

# 26. 日志


记录：

- 扫描
- AI
- 搜索
- 授权
- 错误


---

# 27. 开发原则


必须遵守：


1. UI不写业务逻辑。


2. Service不直接操作SQL。


3. AI模块独立。


4. 所有耗时任务异步。


5. 所有参数配置化。


6. 保持未来云端扩展能力。


---

# 28. MVP开发顺序


Phase1:

项目框架。


Phase2:

照片扫描。


Phase3:

AI索引。


Phase4:

人脸搜索。


Phase5:

授权。


Phase6:

打印。


Phase7:

安装包。

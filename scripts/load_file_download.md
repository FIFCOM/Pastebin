# 文件下载接口压测脚本

`load_file_download.py` 用于压测 Material Bin 的文件下载接口，尤其是带
`encryption_key` 的服务端解密下载路径。

脚本只使用 Python 标准库，不需要额外安装压测工具。

## 适用场景

使用这个脚本来回答这些问题：

- 后端在多少并发下开始无法及时返回响应头。
- 小 Range 请求是否会触发明显延迟或 504。
- 完整文件下载的吞吐和失败率是多少。
- Nginx、网络链路和 FastAPI 直连之间哪个更早成为瓶颈。

不要在生产高峰期直接做大并发压测。优先使用测试环境，或在低峰期逐级增加并发。

## 准备 URL 列表

脚本默认使用这个站点作为基础地址：

```text
https://paste.fifcom.cn
```

可以用环境变量覆盖：

```bash
BASE_URL=https://paste.example.com python scripts/load_file_download.py ...
```

也可以用命令行参数覆盖：

```bash
python scripts/load_file_download.py --base-url https://paste.example.com ...
```

创建一个只用于压测的 URL 文件，例如 `urls.txt`。文件里可以写完整 URL：

```text
https://paste.example.com/api/pastes/PASTE_ID/files/FILE_ID?encryption_key=KEY
https://paste.example.com/api/pastes/PASTE_ID/files/FILE_ID?encryption_key=KEY
```

也可以只写路径；脚本会自动拼接 `BASE_URL`：

```text
/api/pastes/PASTE_ID/files/FILE_ID?encryption_key=KEY
/api/pastes/PASTE_ID/files/FILE_ID?encryption_key=KEY
```

建议准备几类样本：

- 小文件。
- 大文件。
- 有 manifest 的分片文件。
- 怀疑会触发服务端整文件解密的旧文件。

不要把真实敏感文件的 `encryption_key` 放进公开日志、工单或聊天记录。

## 基本命令

单 URL 压测：

```bash
python scripts/load_file_download.py \
  --url '/api/pastes/PASTE_ID/files/FILE_ID?encryption_key=KEY' \
  --concurrency 8 \
  --requests 80 \
  --timeout 60
```

多 URL 阶梯并发：

```bash
python scripts/load_file_download.py \
  --url-file urls.txt \
  --steps 1,2,4,8,16,32 \
  --requests 80 \
  --timeout 60
```

`--requests` 是每个并发档位的总请求数，不是每个 worker 的请求数。

## 测响应头延迟

Nginx 报错：

```text
upstream timed out while reading response header from upstream
```

说明后端没有及时返回响应头。优先使用 `HEAD` 方法观察这个阶段：

```bash
python scripts/load_file_download.py \
  --url-file urls.txt \
  --steps 1,2,4,8,16,32,64 \
  --requests 40 \
  --timeout 30 \
  --method HEAD
```

如果后端或代理不支持 `HEAD`，再使用 `--headers-only` 兼容模式：

```bash
python scripts/load_file_download.py \
  --url-file urls.txt \
  --steps 1,2,4,8,16,32,64 \
  --requests 40 \
  --timeout 30 \
  --headers-only
```

`--headers-only` 会拿到响应头后关闭连接，只用于观察响应头延迟。它可能让 Nginx
access log 里出现额外的 `499`，不要用这个模式判断完整下载成功率。

## 测 Range 请求

使用 `--range` 模拟预览、视频 seek 或小片段请求：

```bash
python scripts/load_file_download.py \
  --url-file urls.txt \
  --steps 1,2,4,8,16,32 \
  --requests 80 \
  --timeout 60 \
  --range 0-1048575
```

`--range` 的值不要带 `bytes=` 前缀。上面的例子表示请求前 1 MiB。

## 测完整下载

完整下载会真实消耗带宽、磁盘 I/O 和后端解密能力：

```bash
python scripts/load_file_download.py \
  --url-file urls.txt \
  --steps 1,2,4,8,16 \
  --requests 20 \
  --timeout 180
```

如果文件较大，先从小并发开始，确认服务器资源还有余量后再增加档位。

## 直连后端与经过 Nginx 对比

先测完整链路：

```bash
python scripts/load_file_download.py \
  --url-file urls.txt \
  --steps 1,2,4,8,16 \
  --requests 40
```

再在服务器上把 URL 换成后端直连地址，例如：

```text
http://127.0.0.1:8000/api/pastes/PASTE_ID/files/FILE_ID?encryption_key=KEY
```

或者保留 `urls.txt` 中的相对路径，通过 `BASE_URL` 切换：

```bash
BASE_URL=http://127.0.0.1:8000 python scripts/load_file_download.py \
  --url-file urls.txt \
  --steps 1,2,4,8,16 \
  --requests 40
```

判断方式：

- 直连后端也失败：瓶颈在 FastAPI、uvicorn、数据库、磁盘或解密。
- 直连后端正常，经过域名失败：瓶颈更可能在 Nginx、TLS、HTTP/2、带宽或代理超时。

## 输出字段

脚本每个并发档位输出一行：

```text
concurrency=8 requests=80 ok=80 failed=0 wall=12.34s rps=6.48 throughput=42.10MiB/s avg=1.020s p50=0.900s p95=1.800s p99=2.100s max=2.300s statuses={'200': 80}
```

字段含义：

- `concurrency`：本轮并发 worker 数。
- `requests`：本轮总请求数。
- `ok`：HTTP 2xx/3xx 请求数。
- `failed`：失败请求数。
- `wall`：本轮总耗时。
- `rps`：每秒完成请求数。
- `throughput`：读取到的响应体吞吐。
- `avg`：平均请求耗时。
- `p50`、`p95`、`p99`：延迟分位数。
- `max`：最大请求耗时。
- `statuses`：HTTP 状态码或错误类型统计。

## 判断并发承受能力

不要把第一次压到失败的档位当作可用容量。

建议把“可承受并发”定义为最后一个满足以下条件的档位：

- `failed` 为 0，或错误率在可接受范围内。
- `statuses` 中没有 `504`、大量 `499` 或连接超时。
- `p95` 和 `p99` 没有突然发散。
- 后端 CPU、内存、文件描述符、数据库连接和磁盘 I/O 都没有顶满。

生产限流值建议设为该档位的 50%-70%。

## 同时观察服务器

压测时同步观察服务端：

```bash
docker stats materialbin
docker logs -f materialbin
grep "upstream timed out" /var/log/nginx/error.log
```

建议临时增强 Nginx access log，加入这些字段：

```nginx
$request_time $upstream_connect_time $upstream_header_time $upstream_response_time
```

判断方式：

- `upstream_header_time` 高：后端返回响应头之前被卡住。
- `upstream_response_time` 高：响应已经开始，但下载流过程慢。
- `request_time` 高但 upstream 时间不高：客户端网络或下行速度可能是主要因素。

## 参数参考

```text
--url URL
```

添加一个压测 URL 或相对路径。可以重复传入多次。

```text
--url-file FILE
```

从文件读取 URL 或相对路径，每行一个。

```text
--base-url URL
```

相对路径使用的基础地址。优先级为 `--base-url`、`BASE_URL` 环境变量、默认
`https://paste.fifcom.cn`。

```text
--concurrency N
```

固定并发数。未传 `--steps` 时生效。

```text
--steps 1,2,4,8
```

阶梯并发列表。传入后会忽略单独的 `--concurrency`。

```text
--requests N
```

每个并发档位执行的总请求数。

```text
--timeout SECONDS
```

单个请求的超时时间。

```text
--method GET|HEAD
```

请求方法。默认是 `GET`。如果只想测响应头延迟，优先尝试 `HEAD`，可以避免
`--headers-only` 提前关闭连接造成的 499 日志。

```text
--range START-END
```

发送 HTTP Range 请求。不要带 `bytes=` 前缀。

```text
--headers-only
```

只等待响应头，不读取响应体。用于隔离响应头延迟，不用于判断完整下载成功率。

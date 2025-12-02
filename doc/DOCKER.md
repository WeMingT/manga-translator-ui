# Docker 使用指南

## 快速开始

### CPU 版本

```bash
# 拉取镜像
docker pull hgmzhn/manga-translator:1.9.2-cpu

# 运行容器
docker run -d \
  --name manga-translator \
  -p 8000:8000 \
  -v $(pwd)/fonts:/app/fonts \
  -v $(pwd)/dict:/app/dict \
  -v $(pwd)/result:/app/result \
  hgmzhn/manga-translator:1.9.2-cpu

# 访问 Web UI
# 打开浏览器访问: http://localhost:8000
```

### GPU 版本（需要 NVIDIA GPU）

```bash
# 拉取镜像
docker pull hgmzhn/manga-translator:1.9.2-gpu

# 运行容器（需要安装 nvidia-docker）
docker run -d \
  --name manga-translator \
  --gpus all \
  -p 8000:8000 \
  -v $(pwd)/fonts:/app/fonts \
  -v $(pwd)/dict:/app/dict \
  -v $(pwd)/result:/app/result \
  hgmzhn/manga-translator:1.9.2-gpu

# 访问 Web UI
# 打开浏览器访问: http://localhost:8000
```

## 详细说明

### 端口映射

- `-p 8000:8000`: 将容器的 8000 端口映射到主机的 8000 端口
- 可以修改主机端口，例如 `-p 9000:8000` 将使用 9000 端口访问

### 数据卷挂载

建议挂载以下目录以持久化数据：

```bash
-v /path/to/fonts:/app/fonts      # 字体文件
-v /path/to/dict:/app/dict        # 提示词文件
-v /path/to/result:/app/result    # 翻译结果
-v /path/to/models:/app/models    # 模型缓存（可选）
```

### 环境变量

可以通过环境变量配置 API Keys：

```bash
docker run -d \
  --name manga-translator \
  -p 8000:8000 \
  -e OPENAI_API_KEY=your_key_here \
  -e GOOGLE_API_KEY=your_key_here \
  -e DEEPL_AUTH_KEY=your_key_here \
  hgmzhn/manga-translator:1.9.2-cpu
```

或使用 .env 文件：

```bash
docker run -d \
  --name manga-translator \
  -p 8000:8000 \
  --env-file .env \
  hgmzhn/manga-translator:1.9.2-cpu
```

### 管理员密码

设置管理员密码（用于访问管理端）：

```bash
docker run -d \
  --name manga-translator \
  -p 8000:8000 \
  -e MANGA_TRANSLATOR_ADMIN_PASSWORD=your_password \
  hgmzhn/manga-translator:1.9.2-cpu
```

## Docker Compose

创建 `docker-compose.yml` 文件：

### CPU 版本

```yaml
version: '3.8'

services:
  manga-translator:
    image: hgmzhn/manga-translator:1.9.2-cpu
    container_name: manga-translator
    ports:
      - "8000:8000"
    volumes:
      - ./fonts:/app/fonts
      - ./dict:/app/dict
      - ./result:/app/result
      - ./models:/app/models
    environment:
      - MANGA_TRANSLATOR_ADMIN_PASSWORD=admin123
      # 添加你的 API Keys
      # - OPENAI_API_KEY=your_key
      # - GOOGLE_API_KEY=your_key
    restart: unless-stopped
```

### GPU 版本

```yaml
version: '3.8'

services:
  manga-translator:
    image: hgmzhn/manga-translator:1.9.2-gpu
    container_name: manga-translator
    ports:
      - "8000:8000"
    volumes:
      - ./fonts:/app/fonts
      - ./dict:/app/dict
      - ./result:/app/result
      - ./models:/app/models
    environment:
      - MANGA_TRANSLATOR_ADMIN_PASSWORD=admin123
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: all
              capabilities: [gpu]
    restart: unless-stopped
```

启动服务：

```bash
docker-compose up -d
```

查看日志：

```bash
docker-compose logs -f
```

停止服务：

```bash
docker-compose down
```

## 常用命令

### 查看容器日志

```bash
docker logs manga-translator
docker logs -f manga-translator  # 实时查看
```

### 进入容器

```bash
docker exec -it manga-translator bash
```

### 停止容器

```bash
docker stop manga-translator
```

### 启动容器

```bash
docker start manga-translator
```

### 删除容器

```bash
docker rm -f manga-translator
```

### 更新镜像

```bash
# 停止并删除旧容器
docker stop manga-translator
docker rm manga-translator

# 拉取新镜像
docker pull hgmzhn/manga-translator:1.9.2-cpu

# 重新运行容器
docker run -d \
  --name manga-translator \
  -p 8000:8000 \
  -v $(pwd)/fonts:/app/fonts \
  -v $(pwd)/dict:/app/dict \
  -v $(pwd)/result:/app/result \
  hgmzhn/manga-translator:1.9.2-cpu
```

## GPU 支持

### 前置要求

1. 安装 NVIDIA 驱动
2. 安装 Docker
3. 安装 NVIDIA Container Toolkit

### 安装 NVIDIA Container Toolkit

Ubuntu/Debian:

```bash
# 添加仓库
distribution=$(. /etc/os-release;echo $ID$VERSION_ID)
curl -s -L https://nvidia.github.io/nvidia-docker/gpgkey | sudo apt-key add -
curl -s -L https://nvidia.github.io/nvidia-docker/$distribution/nvidia-docker.list | \
  sudo tee /etc/apt/sources.list.d/nvidia-docker.list

# 安装
sudo apt-get update
sudo apt-get install -y nvidia-container-toolkit

# 重启 Docker
sudo systemctl restart docker
```

### 验证 GPU 支持

```bash
docker run --rm --gpus all nvidia/cuda:12.1.0-base-ubuntu22.04 nvidia-smi
```

## 故障排除

### 端口被占用

如果 8000 端口被占用，修改端口映射：

```bash
docker run -d -p 9000:8000 ...
```

### 权限问题

如果遇到文件权限问题，可以指定用户 ID：

```bash
docker run -d --user $(id -u):$(id -g) ...
```

### 内存不足

增加 Docker 内存限制：

```bash
docker run -d --memory=8g ...
```

### GPU 不可用

检查 NVIDIA 驱动和 Container Toolkit：

```bash
nvidia-smi
docker run --rm --gpus all nvidia/cuda:12.1.0-base-ubuntu22.04 nvidia-smi
```

## 性能优化

### 模型缓存

挂载模型目录以避免重复下载：

```bash
-v /path/to/models:/app/models
```

### 共享内存

增加共享内存大小（用于大模型）：

```bash
docker run -d --shm-size=2g ...
```

## 安全建议

1. **设置管理员密码**：使用 `MANGA_TRANSLATOR_ADMIN_PASSWORD` 环境变量
2. **不要暴露到公网**：如需公网访问，使用反向代理（Nginx/Caddy）并配置 HTTPS
3. **API Keys 管理**：使用环境变量或 Docker secrets 管理敏感信息
4. **定期更新**：及时更新到最新版本以获取安全补丁

## 更多信息

- GitHub: https://github.com/hgmzhn/manga-translator-ui
- Docker Hub: https://hub.docker.com/r/hgmzhn/manga-translator
- 问题反馈: https://github.com/hgmzhn/manga-translator-ui/issues

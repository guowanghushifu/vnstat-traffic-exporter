# vnstat流量导出器 Makefile

.PHONY: help build run run-bridge stop clean logs shell test backup clean-data logs-info

# 检测Docker Compose命令
DOCKER_COMPOSE_CMD := $(shell \
	if docker compose version >/dev/null 2>&1; then \
		echo "docker compose"; \
	elif command -v docker-compose >/dev/null 2>&1; then \
		echo "docker-compose"; \
	else \
		echo ""; \
	fi)

# 默认目标
help:
	@echo "可用命令:"
	@echo "  build        - 构建Docker镜像"
	@echo "  run          - 使用host网络模式运行 (推荐)"
	@echo "  run-bridge   - 使用bridge网络模式运行"
	@echo "  stop         - 停止容器"
	@echo "  clean        - 停止并删除容器和镜像"
	@echo "  logs         - 查看容器日志"
	@echo "  logs-info    - 查看日志文件信息"
	@echo "  shell        - 进入容器shell"
	@echo "  test         - 测试API接口"
	@echo "  backup       - 备份vnstat数据"
	@echo "  clean-data   - 清理vnstat数据（谨慎使用）"
	@echo ""
	@echo "当前使用: $(DOCKER_COMPOSE_CMD)"

# 构建镜像
build:
	@echo "构建Docker镜像..."
	$(DOCKER_COMPOSE_CMD) build

# 使用host网络模式运行
run:
	@echo "使用host网络模式启动服务..."
	$(DOCKER_COMPOSE_CMD) up -d
	@echo "服务已启动，查看日志请运行: make logs"

# 使用bridge网络模式运行
run-bridge:
	@echo "使用bridge网络模式启动服务..."
	$(DOCKER_COMPOSE_CMD) -f docker-compose.bridge.yml up -d
	@echo "服务已启动，查看日志请运行: make logs"

# 停止容器
stop:
	@echo "停止服务..."
	$(DOCKER_COMPOSE_CMD) down
	$(DOCKER_COMPOSE_CMD) -f docker-compose.bridge.yml down 2>/dev/null || true

# 清理
clean: stop
	@echo "清理Docker资源..."
	docker rmi vnstat-traffic-exporter:latest 2>/dev/null || true
	docker system prune -f

# 查看日志
logs:
	@echo "查看容器日志..."
	$(DOCKER_COMPOSE_CMD) logs -f

# 进入容器shell
shell:
	@echo "进入容器shell..."
	docker exec -it vnstat-exporter /bin/bash

# 测试API
test:
	@echo "测试API接口..."
	@echo "健康检查:"
	curl -s http://localhost:50000/health | python3 -m json.tool || echo "请求失败"
	@echo ""
	@echo "流量数据:"
	curl -s http://localhost:50000/webhook/secret-0c68fb14-bb0d-41ca-a53f-a8ba0ea08fae | python3 -m json.tool || echo "请求失败"

# 备份宿主机vnstat数据
backup:
	@echo "备份宿主机vnstat数据..."
	@if [ -d "/var/lib/vnstat" ]; then \
		sudo tar -czf "vnstat-backup-$(shell date +%Y%m%d-%H%M%S).tar.gz" /var/lib/vnstat/; \
		sudo chown $(shell id -u):$(shell id -g) "vnstat-backup-$(shell date +%Y%m%d-%H%M%S).tar.gz"; \
		echo "✅ 备份完成: vnstat-backup-$(shell date +%Y%m%d-%H%M%S).tar.gz"; \
	else \
		echo "❌ 宿主机vnstat数据目录不存在"; \
	fi

# 显示vnstat状态（不实际删除数据，因为是宿主机数据）
clean-data:
	@echo "⚠️  当前配置使用宿主机vnstat数据库"
	@echo "如需清理数据，请在宿主机上操作："
	@echo "  sudo systemctl stop vnstat"
	@echo "  sudo rm -rf /var/lib/vnstat/*"
	@echo "  sudo systemctl start vnstat"

# 查看日志文件信息
logs-info:
	@echo "📋 容器日志文件信息："
	@echo "配置: 最大10MB/文件, 保留3个文件, 总计最大30MB"
	@echo ""
	@if docker ps -q -f name=vnstat-exporter > /dev/null 2>&1; then \
		echo "当前日志统计:"; \
		docker logs vnstat-exporter 2>&1 | wc -l | awk '{print "  日志行数: " $$1}'; \
		echo "  健康检查频率: 每10分钟"; \
		echo ""; \
		echo "💡 日志管理命令:"; \
		echo "  查看日志: make logs"; \
		echo "  清理日志: docker logs vnstat-exporter --since 0s > /dev/null"; \
	else \
		echo "❌ 容器未运行"; \
	fi 
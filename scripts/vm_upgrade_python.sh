#!/bin/bash
# ═══════════════════════════════════════════════════════════════
# VM Python 3.6 → 3.11 升级脚本
# 使用方式: ssh root@192.168.88.134 < vm_upgrade_python.sh
# 或在 VM 上直接执行: bash vm_upgrade_python.sh
# ═══════════════════════════════════════════════════════════════
set -e

echo "========================================="
echo "  VM Python 升级: → 3.11"
echo "========================================="

# 1. 检测 OS
if [ -f /etc/os-release ]; then
    . /etc/os-release
    OS=$ID
    VER=$VERSION_ID
else
    echo "无法检测 OS，退出"
    exit 1
fi

echo "[1/5] 检测到系统: $OS $VER"
python3 --version 2>/dev/null || echo "当前无 python3"

# 2. 根据 OS 安装 Python 3.11
case "$OS" in
    centos|rhel|rocky|almalinux)
        echo "[2/5] 安装 EPEL + Python 3.11 (yum/dnf)"

        # 安装 EPEL
        if command -v dnf &>/dev/null; then
            sudo dnf install -y epel-release 2>/dev/null || true
            sudo dnf install -y python3.11 python3.11-pip python3.11-devel
        else
            sudo yum install -y epel-release 2>/dev/null || true
            # CentOS 7 需要 IUS 或 SCL 源
            sudo yum install -y centos-release-scl 2>/dev/null || true
            # 尝试从 SCL 安装
            if sudo yum install -y rh-python311 2>/dev/null; then
                echo "Python 3.11 通过 SCL 安装 (rh-python311)"
                echo 'source /opt/rh/rh-python311/enable' | sudo tee /etc/profile.d/python311.sh
                source /opt/rh/rh-python311/enable
            else
                echo "SCL 不可用，尝试从源码编译..."
                INSTALL_SRC=1
            fi
        fi
        ;;
    ubuntu|debian)
        echo "[2/5] 安装 Python 3.11 (apt)"

        sudo apt update -y
        # Ubuntu 22.04+ 自带 Python 3.11
        if dpkg -l python3.11 2>/dev/null | grep -q '^ii'; then
            echo "python3.11 已安装"
        else
            # 尝试从 deadsnakes PPA (Ubuntu) 安装
            if [ "$OS" = "ubuntu" ]; then
                sudo apt install -y software-properties-common
                sudo add-apt-repository -y ppa:deadsnakes/ppa 2>/dev/null || true
                sudo apt update -y
            fi
            sudo apt install -y python3.11 python3.11-venv python3.11-dev python3.11-distutils 2>/dev/null || INSTALL_SRC=1
        fi
        ;;
    *)
        echo "未知 OS: $OS，尝试从源码编译"
        INSTALL_SRC=1
        ;;
esac

# 3. 如果包管理器安装失败，从源码编译
if [ "${INSTALL_SRC:-0}" = "1" ]; then
    echo "[2/5] 从源码编译 Python 3.11.11"

    # 安装编译依赖
    if command -v yum &>/dev/null; then
        sudo yum groupinstall -y "Development Tools" 2>/dev/null || true
        sudo yum install -y gcc gcc-c++ make openssl-devel bzip2-devel libffi-devel zlib-devel readline-devel sqlite-devel 2>/dev/null || true
    elif command -v apt &>/dev/null; then
        sudo apt install -y build-essential libssl-dev libbz2-dev libffi-dev zlib1g-dev libreadline-dev libsqlite3-dev 2>/dev/null || true
    fi

    cd /tmp
    curl -O https://www.python.org/ftp/python/3.11.11/Python-3.11.11.tgz
    tar xzf Python-3.11.11.tgz
    cd Python-3.11.11
    ./configure --enable-optimizations --prefix=/usr/local/python3.11
    make -j$(nproc)
    sudo make altinstall
    sudo ln -sf /usr/local/python3.11/bin/python3.11 /usr/local/bin/python3.11
    sudo ln -sf /usr/local/python3.11/bin/pip3.11 /usr/local/bin/pip3.11
fi

# 4. 设置 python3 → python3.11
echo "[3/5] 设置 python3 默认指向 3.11"
PY311=$(which python3.11 2>/dev/null || echo "/usr/bin/python3.11")
if [ -x "$PY311" ]; then
    sudo alternatives --install /usr/bin/python3 python3 "$PY311" 1 2>/dev/null || true
    sudo alternatives --set python3 "$PY311" 2>/dev/null || true
    # fallback: 直接软链
    sudo ln -sf "$PY311" /usr/local/bin/python3 2>/dev/null || true
fi

# 确保 pip3 可用
PY311_PIP=$(which pip3.11 2>/dev/null || echo "/usr/bin/pip3.11")
if [ -x "$PY311_PIP" ]; then
    sudo alternatives --install /usr/bin/pip3 pip3 "$PY311_PIP" 1 2>/dev/null || true
    sudo ln -sf "$PY311_PIP" /usr/local/bin/pip3 2>/dev/null || true
fi

# 5. 验证
echo "[4/5] 验证安装"
echo "---"
python3.11 --version 2>&1 || echo "python3.11 未找到"
echo "---"
python3 --version 2>&1 || echo "python3 未配置"
echo "---"
pip3 --version 2>&1 || pip3.11 --version 2>&1 || echo "pip3 未找到"

# 6. 安装项目依赖（可选）
echo "[5/5] 数据生成器所需的基础依赖 (pandas, kafka-python)"
if command -v pip3.11 &>/dev/null; then
    pip3.11 install pandas kafka-python 2>&1 | tail -3
elif command -v pip3 &>/dev/null; then
    pip3 install pandas kafka-python 2>&1 | tail -3
fi

echo ""
echo "========================================="
echo "  Python 3.11 安装完成!"
echo "========================================="
echo ""
echo "手动验证:"
echo "  python3.11 --version"
echo "  python3 --version"
echo "  pip3.11 --version"

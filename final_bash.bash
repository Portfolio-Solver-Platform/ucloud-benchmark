#!/bin/bash

# ==========================================
# PARASOL BENCHMARK INSTALLER (FULL & FINAL)
# ==========================================

# Exit immediately if a command exits with a non-zero status
set -e

# --- CONFIGURATION ---
REPO_URL="https://github.com/Portfolio-Solver-Platform/parasol.git"
INSTALL_PATH="/opt/parasol-repo"
MZN_BUNDLE_VERSION="2.9.5"
RUST_VERSION="1.93.0"
MAKE_JOBS=8

# --- PRE-CHECKS ---
if [ "$(id -u)" -ne 0 ]; then
  echo "❌ Please run as root (use sudo)"
  exit 1
fi

echo ">>> Starting Installation..."

# 0. BOOTSTRAP CERTIFICATES (CRITICAL FIX)
# ----------------------------------------
echo ">>> Step 0: Bootstrapping Certificates..."
# Temporarily allow insecure repositories to fetch the certificates.
# We use '|| true' so the script doesn't crash if this update complains.
apt-get update --allow-insecure-repositories || true
apt-get install -y --allow-unauthenticated ca-certificates
# Now update for real
apt-get update -qq

# 1. SYSTEM DEPENDENCIES
# ----------------------
echo ">>> Step 1: Installing System Dependencies..."
apt-get install -y -qq --no-install-recommends \
    default-jre libegl1 software-properties-common \
    curl wget unzip git jq cmake flex bison build-essential \
    gcc libc6-dev

# 2. CLONE REPOSITORY
# -------------------
echo ">>> Step 2: Setting up Repository..."

if [ -d "$INSTALL_PATH" ]; then
    echo "   -> Repository already exists at $INSTALL_PATH. Updating..."
    cd "$INSTALL_PATH"
    git pull
else
    echo "   -> Cloning Parasol to $INSTALL_PATH..."
    git clone "$REPO_URL" "$INSTALL_PATH"
    cd "$INSTALL_PATH"
fi

# Set REPO_ROOT to the path we just cloned into
REPO_ROOT="$INSTALL_PATH"
BUILD_TEMP="${REPO_ROOT}/build_temp"
mkdir -p "$BUILD_TEMP"

echo ">>> Working in: $REPO_ROOT"

# 3. RUST INSTALLATION
# --------------------
echo ">>> Step 3: Setting up Rust $RUST_VERSION..."
export RUSTUP_HOME=/usr/local/rustup
export CARGO_HOME=/usr/local/cargo
export PATH="${CARGO_HOME}/bin:${PATH}"

if ! command -v rustup &> /dev/null; then
    curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y --profile minimal --default-toolchain $RUST_VERSION
else
    rustup install $RUST_VERSION
    rustup default $RUST_VERSION
fi

# 4. MINIZINC BUNDLE (Core + Gecode + Chuffed)
# ---------------------------------------------
echo ">>> Step 4: Processing MiniZinc Bundle..."
cd "$BUILD_TEMP"
if [ ! -f "minizinc.tgz" ]; then
    wget -qO minizinc.tgz "https://github.com/MiniZinc/MiniZincIDE/releases/download/${MZN_BUNDLE_VERSION}/MiniZincIDE-${MZN_BUNDLE_VERSION}-bundle-linux-x86_64.tgz"
fi

rm -rf mzn_bundle && mkdir -p mzn_bundle
tar xf minizinc.tgz -C mzn_bundle --strip-components=1

# A. Install Core MiniZinc
echo "   -> Installing MiniZinc binary..."
cp mzn_bundle/bin/minizinc /usr/local/bin/
cp mzn_bundle/bin/mzn2doc /usr/local/bin/
mkdir -p /usr/local/share/minizinc
cp -r mzn_bundle/share/minizinc/std /usr/local/share/minizinc/
cp -r mzn_bundle/share/minizinc/linear /usr/local/share/minizinc/
cp -r mzn_bundle/lib/libhighs.so /usr/local/lib/
ldconfig

# B. Install Gecode
echo "   -> Installing Gecode..."
mkdir -p /opt/gecode/bin
mkdir -p /opt/gecode/share/minizinc/solvers
mv mzn_bundle/bin/fzn-gecode /opt/gecode/bin/
rm -rf /opt/gecode/lib
mv mzn_bundle/lib /opt/gecode/lib
mv mzn_bundle/share/minizinc/gecode /opt/gecode/share/minizinc/gecode_lib
jq '.executable = "/opt/gecode/bin/fzn-gecode"' mzn_bundle/share/minizinc/solvers/gecode.msc \
 | jq '.mznlib = "/opt/gecode/share/minizinc/gecode_lib"' > /opt/gecode/share/minizinc/solvers/gecode.msc

# C. Install Chuffed
echo "   -> Installing Chuffed..."
mkdir -p /opt/chuffed/bin
mkdir -p /opt/chuffed/share/minizinc/solvers
mv mzn_bundle/bin/fzn-chuffed /opt/chuffed/bin/
mv mzn_bundle/share/minizinc/chuffed /opt/chuffed/share/minizinc/chuffed_lib

# USE TEMPLATE FROM REPO
cp "$REPO_ROOT/minizinc/solvers/chuffed.msc.template" chuffed.msc.template
jq '.executable = "/opt/chuffed/bin/fzn-chuffed"' chuffed.msc.template \
 | jq '.mznlib = "/opt/chuffed/share/minizinc/chuffed_lib"' > /opt/chuffed/share/minizinc/solvers/chuffed.msc

# 5. INSTALL SCIP
# ---------------
echo ">>> Step 5: Installing SCIP..."
if ! command -v scip &> /dev/null; then
    wget -qO scip.deb https://www.scipopt.org/download/release/SCIPOptSuite-9.2.4-Linux-ubuntu24.deb
    apt-get install -y ./scip.deb
    rm scip.deb
fi

# 6. INSTALL HUUB
# ---------------
echo ">>> Step 6: Installing Huub..."
if [ ! -f "/usr/local/bin/fzn-huub" ]; then
    cd "$BUILD_TEMP"
    git clone -q --depth 1 --branch pub/CP2025 https://github.com/huub-solver/huub.git huub_src
    cd huub_src
    cargo build --release --quiet
    cp target/release/fzn-huub /usr/local/bin/fzn-huub
    mkdir -p /usr/local/share/minizinc/huub
    cp -r share/minizinc/huub/* /usr/local/share/minizinc/huub/
    
    # Save the original .msc to temp
    cp share/minizinc/solvers/huub.msc "$BUILD_TEMP/huub.msc.orig"
fi

# 7. INSTALL YUCK
# ---------------
echo ">>> Step 7: Installing Yuck..."
if [ ! -d "/opt/yuck" ]; then
    cd "$BUILD_TEMP"
    YUCK_SHA256="2c562fe76f7b25289dacf90a7688b8cdd2f7c7029676e1d32727f795ac653615"
    wget -q https://github.com/informarte/yuck/releases/download/20251106/yuck-20251106.zip
    echo "${YUCK_SHA256}  yuck-20251106.zip" | sha256sum -c -
    unzip -q yuck-20251106.zip -d /opt
    mv /opt/yuck-20251106 /opt/yuck
    chmod +x /opt/yuck/bin/yuck
fi

# 8. INSTALL OR-TOOLS
# -------------------
echo ">>> Step 8: Installing OR-Tools..."
if [ ! -d "/opt/or-tools" ]; then
    cd "$BUILD_TEMP"
    OR_TOOLS_SHA256="6f389320672cee00b78aacefb2bde33fef0bb988c3b2735573b9fffd1047fbda"
    wget -q https://github.com/google/or-tools/releases/download/v9.15/or-tools_amd64_ubuntu-24.04_cpp_v9.15.6755.tar.gz -O or-tools.tar.gz
    echo "${OR_TOOLS_SHA256}  or-tools.tar.gz" | sha256sum -c -
    mkdir -p or-tools_extract
    tar -xzf or-tools.tar.gz -C or-tools_extract --strip-components=1
    mkdir -p /opt/or-tools
    mv or-tools_extract/bin /opt/or-tools/bin
    mv or-tools_extract/lib /opt/or-tools/lib
    mv or-tools_extract/share /opt/or-tools/share
    
    jq '.executable = "/opt/or-tools/bin/fzn-cp-sat"' /opt/or-tools/share/minizinc/solvers/cp-sat.msc \
     | jq '.mznlib = "/opt/or-tools/share/minizinc/cp-sat"' > cp-sat.msc.temp
    mv cp-sat.msc.temp /opt/or-tools/share/minizinc/solvers/cp-sat.msc
fi

# 9. INSTALL CHOCO
# ----------------
echo ">>> Step 9: Installing Choco..."
if [ ! -d "/opt/choco" ]; then
    cd "$BUILD_TEMP"
    CHOCO_SRC_SHA256="9a6d8c465cc73752c085281f49c45793135d8545e57bc3f4effd15bde6d03de5"
    CHOCO_JAR_SHA256="767a8bdf872c3b9d2a3465bb37822e1f0a60904a54f0181dbf7c6a106415abdf"
    wget -q https://github.com/chocoteam/choco-solver/archive/refs/tags/v4.10.18.tar.gz -O choco.tar.gz
    echo "${CHOCO_SRC_SHA256}  choco.tar.gz" | sha256sum -c -
    wget -q https://github.com/chocoteam/choco-solver/releases/download/v4.10.18/choco-solver-4.10.18-light.jar -O choco.jar
    echo "${CHOCO_JAR_SHA256}  choco.jar" | sha256sum -c -
    
    tar -xzf choco.tar.gz
    mv choco-solver-4.10.18 choco_src
    mkdir -p /opt/choco/bin
    mv choco.jar /opt/choco/bin
    mv choco_src/parsers/src/main/minizinc/fzn-choco.py /opt/choco/bin
    mv choco_src/parsers/src/main/minizinc/fzn-choco.sh /opt/choco/bin
    mkdir -p /opt/choco/share/minizinc/solvers
    mv choco_src/parsers/src/main/minizinc/mzn_lib /opt/choco/share/minizinc/choco_lib
    
    jq '.executable = "/opt/choco/bin/fzn-choco.sh"' choco_src/parsers/src/main/minizinc/choco.msc \
     | jq '.mznlib = "/opt/choco/share/minizinc/choco_lib"' > /opt/choco/share/minizinc/solvers/choco.msc
    sed -i 's&JAR_FILE=.*&JAR_FILE="/opt/choco/bin/choco.jar"&g' /opt/choco/bin/fzn-choco.py
fi

# 10. INSTALL PUMPKIN
# ------------------
echo ">>> Step 10: Installing Pumpkin..."
if [ ! -d "/opt/pumpkin" ]; then
    cd "$BUILD_TEMP"
    PUMPKIN_SHA256="0abf3495945e31c7ebf731bcdc00bae978b6da0b59ff3a8830a0c9335e672ca3"
    wget -q https://github.com/ConSol-Lab/Pumpkin/archive/62b2f09f4b28d0065e4a274d7346f34598b44898.tar.gz -O pumpkin.tar.gz
    echo "${PUMPKIN_SHA256}  pumpkin.tar.gz" | sha256sum -c -
    tar -xzf pumpkin.tar.gz
    mv Pumpkin-62b2f09f4b28d0065e4a274d7346f34598b44898 pumpkin_src
    cd pumpkin_src
    cargo build --release --quiet -p pumpkin-solver
    
    mkdir -p /opt/pumpkin/bin
    mv target/release/pumpkin-solver /opt/pumpkin/bin
    mkdir -p /opt/pumpkin/share/minizinc/solvers
    mv minizinc/lib /opt/pumpkin/share/minizinc/pumpkin_lib
    
    # USE TEMPLATE FROM REPO
    cp "$REPO_ROOT/minizinc/solvers/pumpkin.msc.template" pumpkin.msc.template
    jq '.executable = "/opt/pumpkin/bin/pumpkin-solver"' pumpkin.msc.template \
     | jq '.mznlib = "/opt/pumpkin/share/minizinc/pumpkin_lib"' > /opt/pumpkin/share/minizinc/solvers/pumpkin.msc
fi

# 11. INSTALL DEXTER
# ------------------
echo ">>> Step 11: Installing Dexter..."
if [ ! -d "/opt/dexter" ]; then
    cd "$BUILD_TEMP"
    DEXTER_SHA256="583a5ef689e189a568bd4e691096156fdc1974a0beb9721703f02ba61515b75f"
    wget -qO dexter.tar.gz https://github.com/ddxter/gecode-dexter/archive/b46a6f557977c7b1863dc6b5885b69ebf9edcc14.tar.gz
    echo "${DEXTER_SHA256}  dexter.tar.gz" | sha256sum -c -
    mkdir -p dexter_src
    tar xf dexter.tar.gz -C dexter_src --strip-components=1
    cd dexter_src
    cmake .
    
    # USE MAKE_JOBS HERE
    make -j$MAKE_JOBS
    
    mkdir -p /opt/dexter/bin
    mkdir -p /opt/dexter/share/minizinc/solvers
    mv bin/fzn-gecode /opt/dexter/bin/fzn-dexter
    mv gecode /opt/dexter/share/minizinc/dexter_lib
    
    jq '.executable = "/opt/dexter/bin/fzn-dexter"' tools/flatzinc/gecode.msc.in \
     | jq '.mznlib = "/opt/dexter/share/minizinc/dexter_lib"' > /opt/dexter/share/minizinc/solvers/dexter.msc
fi

# 12. INSTALL MZN2FEAT
# --------------------
echo ">>> Step 12: Installing mzn2feat..."
if [ ! -d "/opt/mzn2feat" ]; then
    cd "$BUILD_TEMP"
    MZN2FEAT_COMMIT="3f92db18a88ba73403238e0ca6be4e9367f4773d"
    MZN2FEAT_SHA256="c5a07a8d4e3d266735302220268bb6e41f136a68e8c3d0bc5c6ee9ec02c8ec2b"
    wget -qO mzn2feat.tar.gz https://github.com/CP-Unibo/mzn2feat/archive/${MZN2FEAT_COMMIT}.tar.gz
    echo "${MZN2FEAT_SHA256}  mzn2feat.tar.gz" | sha256sum -c -
    mkdir -p mzn2feat_src
    tar -xzf mzn2feat.tar.gz -C mzn2feat_src --strip-components=1
    mkdir -p /opt/mzn2feat
    cp -r mzn2feat_src/* /opt/mzn2feat/
    cd /opt/mzn2feat
    bash install --no-xcsp
    
    ln -sf /opt/mzn2feat/bin/mzn2feat /usr/local/bin/mzn2feat
    ln -sf /opt/mzn2feat/bin/fzn2feat /usr/local/bin/fzn2feat
fi

# 13. INSTALL PICAT
# -----------------
echo ">>> Step 13: Installing Picat..."
if [ ! -f "/usr/local/bin/picat" ]; then
    cd "$BUILD_TEMP"
    PICAT_SHA256="938f994ab94c95d308a1abcade0ea04229171304ae2a64ddcea56a49cdd4faa0"
    wget -qO picat.tar.gz https://picat-lang.org/download/picat394_linux64.tar.gz
    echo "${PICAT_SHA256}  picat.tar.gz" | sha256sum -c -
    tar -xzf picat.tar.gz -C /opt
    ln -sf /opt/Picat/picat /usr/local/bin/picat
fi

if [ ! -d "/opt/fzn_picat" ]; then
    cd "$BUILD_TEMP"
    FZN_PICAT_COMMIT="8b6ba4517669bbf856f8b2661b2e8e52d5ad081d"
    FZN_PICAT_SHA256="0ed8995177bd1251ad0433f8c5e7806e0a5a82d96ecc2e20d10b840c4f330b9e"
    wget -qO fzn_picat.tar.gz https://github.com/nfzhou/fzn_picat/archive/${FZN_PICAT_COMMIT}.tar.gz
    echo "${FZN_PICAT_SHA256}  fzn_picat.tar.gz" | sha256sum -c -
    mkdir -p /opt/fzn_picat
    tar -xzf fzn_picat.tar.gz -C /opt/fzn_picat --strip-components=1
fi

# 14. BUILD PARASOL (THE MAIN APP)
# -------------------------------
echo ">>> Step 14: Building Parasol..."
cd "$REPO_ROOT"
cargo build --release --locked --quiet
cp target/release/parasol /usr/local/bin/parasol

# 15. PYTHON ENV
# --------------
echo ">>> Step 15: Setting up Python..."
add-apt-repository -y ppa:deadsnakes/ppa
apt-get update -qq
# Python venv usually includes pip, adding python3-pip to be safe
apt-get install -y python3.13 python3.13-venv python3-pip

if [ -f "$REPO_ROOT/command-line-ai/requirements.txt" ]; then
    echo "   -> Installing requirements..."
    python3.13 -m pip install --quiet --break-system-packages --ignore-installed -r "$REPO_ROOT/command-line-ai/requirements.txt"
fi

# Copy command-line-ai folder
echo "   -> Copying command-line-ai..."
rm -rf /opt/command-line-ai
if [ -d "$REPO_ROOT/command-line-ai" ]; then
    cp -r "$REPO_ROOT/command-line-ai" /opt/command-line-ai
else
    echo "⚠️ Warning: command-line-ai folder not found in repo."
fi

# 16. FINAL CONFIGURATION
# -----------------------
echo ">>> Step 16: Finalizing Configuration..."
SOLVER_CONFIG_DIR="/usr/local/share/minizinc/solvers"
mkdir -p "$SOLVER_CONFIG_DIR"

# Copy solver configs from /opt
cp /opt/or-tools/share/minizinc/solvers/*.msc "$SOLVER_CONFIG_DIR/" || true
cp /opt/choco/share/minizinc/solvers/*.msc "$SOLVER_CONFIG_DIR/" || true
cp /opt/pumpkin/share/minizinc/solvers/*.msc "$SOLVER_CONFIG_DIR/" || true
cp /opt/gecode/share/minizinc/solvers/*.msc "$SOLVER_CONFIG_DIR/" || true
cp /opt/chuffed/share/minizinc/solvers/*.msc "$SOLVER_CONFIG_DIR/" || true
cp /opt/dexter/share/minizinc/solvers/*.msc "$SOLVER_CONFIG_DIR/" || true

# Config Huub
if [ -f "$BUILD_TEMP/huub.msc.orig" ]; then
    jq '.executable = "/usr/local/bin/fzn-huub"' "$BUILD_TEMP/huub.msc.orig" \
    | jq '.mznlib = "/usr/local/share/minizinc/huub/"' > "$SOLVER_CONFIG_DIR/huub.msc"
fi

# Config Yuck
cp /opt/yuck/mzn/yuck.msc "$BUILD_TEMP/yuck.msc.template"
jq '.executable = "/opt/yuck/bin/yuck"' "$BUILD_TEMP/yuck.msc.template" \
 | jq '.mznlib = "/opt/yuck/mzn/lib/"' > "$SOLVER_CONFIG_DIR/yuck.msc"

# Config Parasol
cd "$BUILD_TEMP"
cp "$REPO_ROOT/minizinc/solvers/parasol.msc.template" parasol.msc.template
jq '.executable[0] = "/usr/local/bin/parasol"' parasol.msc.template > "$SOLVER_CONFIG_DIR/parasol.msc"

# Config Picat
if [ -f "$REPO_ROOT/solvers/picat/wrapper.sh" ]; then
    cp "$REPO_ROOT/solvers/picat/wrapper.sh" /usr/local/bin/fzn-picat
    chmod +x /usr/local/bin/fzn-picat
else
    # Create simple wrapper if missing
    echo '#!/bin/bash' > /usr/local/bin/fzn-picat
    echo 'exec /usr/local/bin/picat /opt/fzn_picat/fzn_picat.pi "$@"' >> /usr/local/bin/fzn-picat
    chmod +x /usr/local/bin/fzn-picat
fi

cd "$BUILD_TEMP"
cp "$REPO_ROOT/minizinc/solvers/picat.msc.template" picat.msc.template
jq '.executable = "/usr/local/bin/fzn-picat"' picat.msc.template \
 | jq '.mznlib = "/opt/fzn_picat/mznlib"' > "$SOLVER_CONFIG_DIR/picat.msc"

# Minizinc Preferences
mkdir -p /home/ucloud/.minizinc/
if [ -f "$REPO_ROOT/minizinc/Preferences.json" ]; then
    cp "$REPO_ROOT/minizinc/Preferences.json" /home/ucloud/.minizinc/
else
    echo "⚠️ Warning: minizinc/Preferences.json not found in repo."
fi

# Static Schedules
if [ -d "$REPO_ROOT/static-schedules" ]; then
    cp -r "$REPO_ROOT/static-schedules" /static-schedules
else
    echo "⚠️ Warning: static-schedules folder not found."
fi

# Register Libraries (Critical for Gecode AND MiniZinc)
echo "/opt/gecode/lib" > /etc/ld.so.conf.d/gecode.conf
ldconfig

# 17. OPTIONAL SOLVERS (CPLEX/XPRESS)
# -----------------------------------
echo ">>> Step 17: Checking for Optional Solvers..."

# CPLEX
if [ -f "$REPO_ROOT/libcplex.so" ]; then
    echo "   -> Found libcplex.so, installing..."
    cp "$REPO_ROOT/libcplex.so" /usr/local/lib/
    chmod 755 /usr/local/lib/libcplex.so
    ldconfig
fi

# XPRESS
if [ -d "$REPO_ROOT/xpressmp" ]; then
    echo "   -> Found xpressmp folder, installing..."
    rm -rf /opt/xpressmp
    cp -r "$REPO_ROOT/xpressmp" /opt/xpressmp
    echo "/opt/xpressmp/lib" > /etc/ld.so.conf.d/xpress.conf
    ldconfig
fi

# 18. CACHE BUILD
# ---------------
echo ">>> Step 18: Building Solver Cache..."
parasol build-solver-cache

# Cleanup
rm -rf "$BUILD_TEMP"

mv /opt/parasol-repo /app
chown ucloud:ucloud /app -R

unzip /work/benchmark/xpressmp.zip -d /work
cp -r /work/xpressmp /opt/xpressmp

echo "=========================================="
echo "✅ INSTALLATION COMPLETE"
echo "   Repository is located at: $INSTALL_PATH"
echo "=========================================="
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
cron: 9 0,13 * * *
new Env('NCMM 任务执行')

NCMM 任务执行脚本 (Wzhuaboy/ncmm fork, 环境变量开关版)
====================================================
原版只认 RUN_ARGS = ["task"], 任务开关只能改 config.yaml。
本版在原版基础上加了 8 个环境变量开关, 在青龙面板
环境变量里填 true / false 就能开 / 关对应任务, 不用改文件。

环境变量 (不填 = 用默认值, 默认值跟 config.yaml 里 task: 一致):
  NCMM_TASK_SIGN=true              日常签到 (云贝 + 黑胶成长值)
  NCMM_TASK_PLAYIDS=true           播放指定歌曲
  NCMM_TASK_MUSICIAN_SIGN=true     音乐人日常签到
  NCMM_TASK_MUSICIAN_VIP=true      音乐人 VIP 进阶
  NCMM_TASK_DAILY_SONG_SHARE=false 每日推歌 + 抽奖 (需要移动端 Token, 网页 Cookie 会跳过)
  NCMM_TASK_VIP_MEMBER_GIFT=true   黑胶会员礼品赠送 / 领取
  NCMM_TASK_FANSGROUP=false        乐迷团打卡 (需在 config.yaml 配 groupIds)
  NCMM_TASK_NOTE=false             发布图文笔记
  NCMM_TASK_ONLY_FAST=false        只跑快任务组 (跟上面 8 项二选一, 优先于单项)
  NCMM_TASK_ONLY_SLOW=false        只跑慢任务组 (跟上面 8 项二选一)

取值: true / 1 / yes / on = 开, false / 0 / no / off = 关, 大小写不限。
8 项全关时不执行任何任务, 直接退出, 日志会写明。
"""

import os
import sys
import platform
import subprocess

# ============ 环境变量任务开关 ============
# (环境变量名, ncmm task 的 flag, 默认值)
TASK_FLAGS = [
    ("NCMM_TASK_SIGN", "--sign", True),
    ("NCMM_TASK_PLAYIDS", "--playids", True),
    ("NCMM_TASK_MUSICIAN_SIGN", "--musician-sign", True),
    ("NCMM_TASK_MUSICIAN_VIP", "--musician-vip", True),
    ("NCMM_TASK_DAILY_SONG_SHARE", "--daily-song-share", False),
    ("NCMM_TASK_VIP_MEMBER_GIFT", "--vip-member-gift", True),
    ("NCMM_TASK_FANSGROUP", "--fansgroup", False),
    ("NCMM_TASK_NOTE", "--note", False),
]


def env_bool(name, default):
    """读一个 true/false 环境变量, 未设置或值非法时用默认值."""
    raw = os.getenv(name)
    if raw is None:
        return default
    val = raw.strip().lower()
    if val in ("true", "1", "yes", "on"):
        return True
    if val in ("false", "0", "no", "off", ""):
        return False
    print(f"[WARNING] 环境变量 {name}={raw!r} 无法识别, 按默认值 {default} 处理")
    return default


def build_run_args():
    """按环境变量开关拼出 RUN_ARGS, 即 ./ncmm task [flags]."""
    only_fast = env_bool("NCMM_TASK_ONLY_FAST", False)
    only_slow = env_bool("NCMM_TASK_ONLY_SLOW", False)
    if only_fast and only_slow:
        print("[WARNING] NCMM_TASK_ONLY_FAST 和 NCMM_TASK_ONLY_SLOW 同时为 true, 只用 --only-fast")
        only_slow = False
    if only_fast:
        print("[LOG] 任务开关: 只跑快任务组 (--only-fast)")
        return ["task", "--only-fast"]
    if only_slow:
        print("[LOG] 任务开关: 只跑慢任务组 (--only-slow)")
        return ["task", "--only-slow"]

    enabled = []
    states = []
    for env_name, flag, default in TASK_FLAGS:
        on = env_bool(env_name, default)
        states.append(f"{env_name}={'true' if on else 'false'}")
        if on:
            enabled.append(flag)
    print(f"[LOG] 任务开关: {', '.join(states)}")
    if not enabled:
        print("[LOG] 8 项任务开关均为 false, 未执行任何任务")
        sys.exit(0)
    return ["task"] + enabled


RUN_ARGS = build_run_args()
# ========================================

# 获取当前脚本所在的真实目录
current_dir = os.path.dirname(os.path.abspath(__file__))

# 判断二进制文件名
is_windows = 'windows' in platform.system().lower()
binary_name = "ncmm.exe" if is_windows else "ncmm"
binary_path = os.path.join(current_dir, binary_name)

# 检查 ncmm 是否存在，若不存在则自动调用 ncmm-update.py 下载安装
if not os.path.exists(binary_path):
    print(f"[LOG] 未在 {current_dir} 找到 {binary_name}，正在自动调用 ncmm-update.py 下载程序...")
    update_script = os.path.join(current_dir, "ncmm-update.py")
    if os.path.exists(update_script):
        update_cmd = [sys.executable, update_script]
        print(f"[LOG] 正在自动执行安装: {' '.join(update_cmd)}")
        res = subprocess.run(update_cmd, cwd=current_dir)
        if res.returncode != 0:
            print(f"[ERROR] 自动调用 ncmm-update.py 安装失败 (exit code: {res.returncode})，请检查网络或配置。")
            sys.exit(res.returncode)
    else:
        print(f"[ERROR] 未找到安装脚本 {update_script}，无法自动下载。")
        sys.exit(1)

    # 再次检查二进制文件是否存在
    if not os.path.exists(binary_path):
        print(f"[ERROR] 自动运行 ncmm-update.py 完成后，仍未找到 {binary_name}。")
        sys.exit(1)

# 运行 ncmm
# 2026-11-04 修复: 原版只跑 ./ncmm task, 不传 -c, 程序默认只找
# --home/config.yaml 和 ${HOME}/.ncmm/config.yaml, 找不到就用内置
# 默认配置, 所以 scripts/config.yaml 里改的 groupIds 从来没生效。
# 这里明确用 -c 指向脚本同目录的 config.yaml, --home 不动,
# Cookie/数据库/日志路径保持原样, 只改配置来源。
config_path = os.path.join(current_dir, "config.yaml")
cmd = [binary_path, "-c", config_path] + RUN_ARGS
print(f"[LOG] 配置文件: {config_path}")
print(f"[LOG] 正在执行: {' '.join(cmd)}")
result = subprocess.run(cmd, cwd=current_dir)
sys.exit(result.returncode)

"""批量生成所有系统音色的预览音频"""
import os, time, requests, tarfile, uuid
from dotenv import load_dotenv
load_dotenv()

API_KEY = os.getenv("MINIMAX_API_KEY", "")
BASE_URL = "https://api.minimaxi.com"
HEADERS_AUTH = {"Authorization": f"Bearer {API_KEY}"}
HEADERS_JSON = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
SAMPLES_DIR = os.path.join(PROJECT_ROOT, "ref", "api", "voice", "samples")
os.makedirs(SAMPLES_DIR, exist_ok=True)

TEST_SCRIPTS = {
    "zh": "欢迎收听本期期货投资教育节目。今日甲醇主力合约稳稳站在2850元附近，核心支撑来自进口端伊朗装置全面停车，5月进口将大幅缩减。基本面偏强，但投资者仍需注意仓位管理，理性看待行情波动。",
    "en": "Welcome to today's futures market update. Methanol futures held steady around 2850 yuan, supported by tightening supply as Iranian facilities suspend operations. Trade prudently and manage risk wisely.",
    "ja": "本日の先物市場をお届けします。メ甲醇の先物価格は2850元付近で底堅く推移しており、伊朗の設備停止が供給を引き締められています。リスク管理を怠らないようご注意ください。",
}

VOICES = [
    ("Chinese (Mandarin)_Reliable_Executive", "沉稳高管", "zh"),
    ("Chinese (Mandarin)_News_Anchor", "新闻女声", "zh"),
    ("Chinese (Mandarin)_Mature_Woman", "傲娇御姐", "zh"),
    ("Chinese (Mandarin)_Unrestrained_Young_Man", "不羁青年", "zh"),
    ("Chinese (Mandarin)_Humorous_Elder", "搞笑大爷", "zh"),
    ("Chinese (Mandarin)_Gentleman", "温润男声", "zh"),
    ("Chinese (Mandarin)_Warm_Bestie", "温暖闺蜜", "zh"),
    ("Chinese (Mandarin)_Male_Announcer", "播报男声", "zh"),
    ("Chinese (Mandarin)_Sweet_Lady", "甜美女声", "zh"),
    ("Chinese (Mandarin)_Southern_Young_Man", "南方小哥", "zh"),
    ("Chinese (Mandarin)_Wise_Women", "阅历姐姐", "zh"),
    ("Chinese (Mandarin)_Gentle_Youth", "温润青年", "zh"),
    ("Chinese (Mandarin)_Warm_Girl", "温暖少女", "zh"),
    ("Chinese (Mandarin)_Kind-hearted_Elder", "花甲奶奶", "zh"),
    ("Chinese (Mandarin)_Cute_Spirit", "憨憨萌兽", "zh"),
    ("Chinese (Mandarin)_Radio_Host", "电台男主播", "zh"),
    ("Chinese (Mandarin)_Lyrical_Voice", "抒情男声", "zh"),
    ("Chinese (Mandarin)_Straightforward_Boy", "率真弟弟", "zh"),
    ("Chinese (Mandarin)_Sincere_Adult", "真诚青年", "zh"),
    ("Chinese (Mandarin)_Gentle_Senior", "温柔学姐", "zh"),
    ("Chinese (Mandarin)_Soft_Girl", "软软女孩", "zh"),
    ("Chinese (Mandarin)_Crisp_Girl", "清脆少女", "zh"),
    ("Chinese (Mandarin)_Pure-hearted_Boy", "清澈邻家弟弟", "zh"),
    ("Chinese (Mandarin)_Stubborn_Friend", "嘴硬竹马", "zh"),
    ("Chinese (Mandarin)_HK_Flight_Attendant", "港普空姐", "zh"),
    ("Chinese (Mandarin)_Kind-hearted_Antie", "热心大婶", "zh"),
    ("Cantonese_ProfessionalHost（F)", "专业女主持(粤)", "zh"),
    ("Cantonese_GentleLady", "温柔女声(粤)", "zh"),
    ("Cantonese_CuteGirl", "可爱女孩(粤)", "zh"),
    ("Cantonese_KindWoman", "善良女声(粤)", "zh"),
    ("Cantonese_PlayfulMan", "活泼男声(粤)", "zh"),
    ("Cantonese_ProfessionalHost（M)", "专业男主持(粤)", "zh"),
    ("female-shaonv", "少女音色", "zh"),
    ("female-yujie", "御姐音色", "zh"),
    ("female-chengshu", "成熟女声", "zh"),
    ("female-tianmei", "甜美女声", "zh"),
    ("male-qn-jingying", "精英男声", "zh"),
    ("male-qn-badao", "霸道男声", "zh"),
    ("male-qn-qingse", "青涩男声", "zh"),
    ("male-qn-daxuesheng", "大学生男声", "zh"),
    ("English_Graceful_Lady", "Graceful Lady", "en"),
    ("English_Trustworthy_Man", "Trustworthy Man", "en"),
    ("English_Gentle-voiced_man", "Gentle-voiced Man", "en"),
    ("English_Aussie_Bloke", "Aussie Bloke", "en"),
    ("English_Diligent_Man", "Diligent Man", "en"),
    ("English_Whispering_girl", "Whispering Girl", "en"),
    ("Japanese_CalmLady", "Calm Lady", "ja"),
    ("Japanese_ColdQueen", "Cold Queen", "ja"),
    ("Japanese_DecisivePrincess", "Decisive Princess", "ja"),
    ("Japanese_GentleButler", "Gentle Butler", "ja"),
    ("Japanese_KindLady", "Kind Lady", "ja"),
    ("Japanese_OptimisticYouth", "Optimistic Youth", "ja"),
    ("Japanese_SeriousCommander", "Serious Commander", "ja"),
    ("Japanese_LoyalKnight", "Loyal Knight", "ja"),
    ("Japanese_DominantMan", "Dominant Man", "ja"),
    ("Japanese_IntellectualSenior", "Intellectual Senior", "ja"),
]

def wait_task(task_id):
    for i in range(60):
        time.sleep(5)
        resp = requests.get(f"{BASE_URL}/v1/query/t2a_async_query_v2?task_id={task_id}", headers=HEADERS_AUTH)
        r = resp.json()
        status = r.get("status", "Processing")
        print(f"  [{i+1}] {status}", flush=True)
        if status == "Success":
            return "Success"
        if status in ("Failed", "Expired"):
            return status
    return "Timeout"

def generate_one(voice_id, voice_name, lang):
    script = TEST_SCRIPTS.get(lang, TEST_SCRIPTS["zh"])
    print(f"[生成] {voice_name} ({voice_id})")

    # 1. 创建T2S任务
    payload = {
        "model": "speech-2.8-hd",
        "text": script,
        "voice_setting": {"voice_id": voice_id, "speed": 1.0, "vol": 1.0, "pitch": 0},
        "audio_setting": {"audio_sample_rate": 32000, "bitrate": 128000, "format": "mp3", "channel": 1},
    }
    resp = requests.post(f"{BASE_URL}/v1/t2a_async_v2", headers=HEADERS_JSON, json=payload)
    if resp.status_code != 200:
        print(f"  [FAIL] HTTP {resp.status_code}: {resp.text[:150]}")
        return False
    result = resp.json()
    if result.get("base_resp", {}).get("status_code") != 0:
        print(f"  [FAIL] API错误: {result}")
        return False

    task_id = result["task_id"]
    file_id = result["file_id"]
    print(f"  task_id={task_id}，等待完成...", end="", flush=True)

    # 2. 轮询
    status = wait_task(task_id)
    if status != "Success":
        print(f"  [FAIL] 任务状态: {status}")
        return False

    # 3. 下载tar并解压
    dl_resp = requests.get(f"{BASE_URL}/v1/files/retrieve?file_id={file_id}", headers=HEADERS_AUTH)
    dl_data = dl_resp.json()
    download_url = dl_data.get("file", {}).get("download_url", "")
    if not download_url:
        print(f"  [FAIL] 获取下载链接失败")
        return False

    tar_resp = requests.get(download_url)
    run_id = str(uuid.uuid4())[:8]
    out_dir = os.path.join(SAMPLES_DIR, run_id)
    os.makedirs(out_dir, exist_ok=True)

    tar_path = os.path.join(out_dir, "output.tar")
    with open(tar_path, "wb") as f:
        f.write(tar_resp.content)

    mp3_name = None
    with tarfile.open(tar_path, "r") as tar:
        for member in tar.getmembers():
            if member.name.endswith(".mp3"):
                member.name = os.path.basename(member.name)
                tar.extract(member, out_dir)
                mp3_name = member.name
                break

    if not mp3_name:
        print(f"  [FAIL] 解压MP3失败")
        return False

    relative_path = f"ref/api/voice/samples/{run_id}/{mp3_name}"
    print(f"  [OK] 保存: {relative_path}")
    return True

if __name__ == "__main__":
    success = 0
    fail = 0
    for voice_id, voice_name, lang in VOICES:
        ok = generate_one(voice_id, voice_name, lang)
        if ok:
            success += 1
        else:
            fail += 1
        time.sleep(1)  # 避免触发限流
    print(f"\n完成: 成功 {success}，失败 {fail}")

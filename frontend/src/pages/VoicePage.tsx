import { useState, useRef } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { voicesApi } from "../api/voices";
import { audioApi, type AudioGenerateParams } from "../api/audio";
import type { VoiceSampleResponse } from "../types";

// 所有系统音色（含用户提供的完整列表 + 说明）
const SYSTEM_VOICES: VoiceDef[] = [
  // ── 中文普通话 ────────────────────────────────────────────
  { voice_id: "Chinese (Mandarin)_Reliable_Executive", voice_name: "沉稳高管", lang: "zh", desc: "一位沉稳可靠的中年男性高管声音，标准普通话，传递出值得信赖的感觉。" },
  { voice_id: "Chinese (Mandarin)_News_Anchor", voice_name: "新闻女声", lang: "zh", desc: "一位专业、播音腔的中年女性新闻主播，标准普通话。" },
  { voice_id: "Chinese (Mandarin)_Mature_Woman", voice_name: "傲娇御姐", lang: "zh", desc: "一位妩媚成熟的青年御姐声音，标准普通话。" },
  { voice_id: "Chinese (Mandarin)_Unrestrained_Young_Man", voice_name: "不羁青年", lang: "zh", desc: "一位潇洒不羁的青年男性声音，标准普通话。" },
  { voice_id: "Chinese (Mandarin)_Humorous_Elder", voice_name: "搞笑大爷", lang: "zh", desc: "一位爽朗幽默的老年男性大爷声音，带有北方口音的中文，充满个性。" },
  { voice_id: "Chinese (Mandarin)_Gentleman", voice_name: "温润男声", lang: "zh", desc: "一位温润磁性的青年男性声音，标准普通话。" },
  { voice_id: "Chinese (Mandarin)_Warm_Bestie", voice_name: "温暖闺蜜", lang: "zh", desc: "一位温暖清脆的青年女性闺蜜声音，标准普通话，友好而清晰。" },
  { voice_id: "Chinese (Mandarin)_Male_Announcer", voice_name: "播报男声", lang: "zh", desc: "一位富有磁性的中年男性播报员声音，标准普通话，清晰而权威。" },
  { voice_id: "Chinese (Mandarin)_Sweet_Lady", voice_name: "甜美女声", lang: "zh", desc: "一位温柔甜美的青年女性声音，标准普通话。" },
  { voice_id: "Chinese (Mandarin)_Southern_Young_Man", voice_name: "南方小哥", lang: "zh", desc: "一位质朴的青年男性声音，带有南方口音的中文。" },
  { voice_id: "Chinese (Mandarin)_Wise_Women", voice_name: "阅历姐姐", lang: "zh", desc: "一位富有阅历、声音抒情的中年姐姐声音，标准普通话。" },
  { voice_id: "Chinese (Mandarin)_Gentle_Youth", voice_name: "温润青年", lang: "zh", desc: "一位温柔的青年男性声音，标准普通话。" },
  { voice_id: "Chinese (Mandarin)_Warm_Girl", voice_name: "温暖少女", lang: "zh", desc: "一位温柔温暖的少年女声，标准普通话。" },
  { voice_id: "Chinese (Mandarin)_Kind-hearted_Elder", voice_name: "花甲奶奶", lang: "zh", desc: "一位慈祥和蔼的老年女性奶奶声音，标准普通话。" },
  { voice_id: "Chinese (Mandarin)_Cute_Spirit", voice_name: "憨憨萌兽", lang: "zh", desc: "一位呆萌可爱的少年男声，适合憨厚的萌兽角色。" },
  { voice_id: "Chinese (Mandarin)_Radio_Host", voice_name: "电台男主播", lang: "zh", desc: "一位富有诗意的青年男性电台主播声音，标准普通话，声音流畅引人入胜。" },
  { voice_id: "Chinese (Mandarin)_Lyrical_Voice", voice_name: "抒情男声", lang: "zh", desc: "一位磁性抒情的青年男性声音，标准普通话，流畅而富有表现力。" },
  { voice_id: "Chinese (Mandarin)_Straightforward_Boy", voice_name: "率真弟弟", lang: "zh", desc: "一位认真率真的少年弟弟声音，标准普通话。" },
  { voice_id: "Chinese (Mandarin)_Sincere_Adult", voice_name: "真诚青年", lang: "zh", desc: "一位真诚、富有鼓励性的青年男性声音，标准普通话。" },
  { voice_id: "Chinese (Mandarin)_Gentle_Senior", voice_name: "温柔学姐", lang: "zh", desc: "一位温暖温柔的青年学姐声音，标准普通话。" },
  { voice_id: "Chinese (Mandarin)_Soft_Girl", voice_name: "软软女孩", lang: "zh", desc: "一位温暖柔软的青年女性声音，带有南方口音的中文。" },
  { voice_id: "Chinese (Mandarin)_Crisp_Girl", voice_name: "清脆少女", lang: "zh", desc: "一位温暖清脆的少女声音，标准普通话。" },
  { voice_id: "Chinese (Mandarin)_Pure-hearted_Boy", voice_name: "清澈邻家弟弟", lang: "zh", desc: "一位认真清澈的邻家少年弟弟声音，标准普通话。" },
  { voice_id: "Chinese (Mandarin)_Stubborn_Friend", voice_name: "嘴硬竹马", lang: "zh", desc: "一位嘴硬心软、不羁的青年竹马声音，标准普通话。" },
  { voice_id: "Chinese (Mandarin)_HK_Flight_Attendant", voice_name: "港普空姐", lang: "zh", desc: "一位礼貌的中年女性空乘员声音，带有港式普通话口音，清晰而有礼。" },
  { voice_id: "Chinese (Mandarin)_Kind-hearted_Antie", voice_name: "热心大婶", lang: "zh", desc: "一位温和善良的中年大婶声音，标准普通话，温暖而体贴。" },
  // ── 中文粤语 ──────────────────────────────────────────────
  { voice_id: "Cantonese_ProfessionalHost（F)", voice_name: "专业女主持(粤)", lang: "zh", desc: "一位中性、专业的青年女性粤语主持人声音。" },
  { voice_id: "Cantonese_GentleLady", voice_name: "温柔女声(粤)", lang: "zh", desc: "一位平静温柔的青年女性粤语声音。" },
  { voice_id: "Cantonese_CuteGirl", voice_name: "可爱女孩(粤)", lang: "zh", desc: "一位柔和可爱的青年女性粤语声音。" },
  { voice_id: "Cantonese_KindWoman", voice_name: "善良女声(粤)", lang: "zh", desc: "一位亲切善良的青年女性粤语声音。" },
  { voice_id: "Cantonese_PlayfulMan", voice_name: "活泼男声(粤)", lang: "zh", desc: "一位活泼深情的青年男性粤语声音。" },
  { voice_id: "Cantonese_ProfessionalHost（M)", voice_name: "专业男主持(粤)", lang: "zh", desc: "一位中性、专业的青年男性粤语主持人声音。" },
  // ── 经典音色 ──────────────────────────────────────────────
  { voice_id: "female-shaonv", voice_name: "少女音色", lang: "zh", desc: "清新少女声音。" },
  { voice_id: "female-yujie", voice_name: "御姐音色", lang: "zh", desc: "成熟御姐声音。" },
  { voice_id: "female-chengshu", voice_name: "成熟女声", lang: "zh", desc: "成熟女性声音。" },
  { voice_id: "female-tianmei", voice_name: "甜美女声", lang: "zh", desc: "甜美女性声音。" },
  { voice_id: "male-qn-jingying", voice_name: "精英男声", lang: "zh", desc: "精英男性声音。" },
  { voice_id: "male-qn-badao", voice_name: "霸道男声", lang: "zh", desc: "霸道男性声音。" },
  { voice_id: "male-qn-qingse", voice_name: "青涩男声", lang: "zh", desc: "青涩男性声音。" },
  { voice_id: "male-qn-daxuesheng", voice_name: "大学生男声", lang: "zh", desc: "大学生男性声音。" },
  // ── 英文 ─────────────────────────────────────────────────
  { voice_id: "English_Graceful_Lady", voice_name: "Graceful Lady", lang: "en", desc: "一位优雅的中年女士，带有经典的英式口音。" },
  { voice_id: "English_Trustworthy_Man", voice_name: "Trustworthy Man", lang: "en", desc: "一位值得信赖、富有磁性的青年男性声音。" },
  { voice_id: "English_Gentle-voiced_man", voice_name: "Gentle-voiced Man", lang: "en", desc: "一位声音温柔、富有磁性的青年男性。" },
  { voice_id: "English_Aussie_Bloke", voice_name: "Aussie Bloke", lang: "en", desc: "一位阳光开朗的青年男性，带有独特的澳大利亚口音。" },
  { voice_id: "English_Diligent_Man", voice_name: "Diligent Man", lang: "en", desc: "一位真诚勤奋的青年男性，带有印度口音。" },
  { voice_id: "English_Whispering_girl", voice_name: "Whispering Girl", lang: "en", desc: "一位青年女性的轻柔耳语声，非常适合ASMR内容。" },
  // ── 日文 ─────────────────────────────────────────────────
  { voice_id: "Japanese_CalmLady", voice_name: "Calm Lady", lang: "ja", desc: "一位沉静迷人的青年女性声音。" },
  { voice_id: "Japanese_ColdQueen", voice_name: "Cold Queen", lang: "ja", desc: "一位冷漠的青年女王声音。" },
  { voice_id: "Japanese_DecisivePrincess", voice_name: "Decisive Princess", lang: "ja", desc: "一位坚定果断的青年公主声音。" },
  { voice_id: "Japanese_GentleButler", voice_name: "Gentle Butler", lang: "ja", desc: "一位迷人温柔的青年男性管家声音。" },
  { voice_id: "Japanese_KindLady", voice_name: "Kind Lady", lang: "ja", desc: "一位迷人善良的青年女性声音。" },
  { voice_id: "Japanese_OptimisticYouth", voice_name: "Optimistic Youth", lang: "ja", desc: "一位开朗乐观的青年男性声音。" },
  { voice_id: "Japanese_SeriousCommander", voice_name: "Serious Commander", lang: "ja", desc: "一位严肃可靠的青年男性指挥官声音。" },
  { voice_id: "Japanese_LoyalKnight", voice_name: "Loyal Knight", lang: "ja", desc: "一位年轻忠诚的青年男性骑士声音。" },
  { voice_id: "Japanese_DominantMan", voice_name: "Dominant Man", lang: "ja", desc: "一位成熟强势的中年男性声音。" },
  { voice_id: "Japanese_IntellectualSenior", voice_name: "Intellectual Senior", lang: "ja", desc: "一位成熟知性的青年男性声音。" },
];

// 统一的测试脚本（中文音色用，稍长的期货主题句子）
const TEST_SCRIPTS: Record<string, string> = {
  zh: "欢迎收听本期期货投资教育节目。今日甲醇主力合约稳稳站在2850元附近，核心支撑来自进口端伊朗装置全面停车，5月进口将大幅缩减。基本面偏强，但投资者仍需注意仓位管理，理性看待行情波动。",
  en: "Welcome to today's futures market update. Methanol futures held steady around 2,850 yuan, supported by tightening supply as Iranian facilities suspend operations. Trade prudently and manage risk wisely.",
  ja: "本日の先物市場をお届けします。メ甲醇の先物価格は2850元付近で底堅く推移しており、伊朗の設備停止が供給を引き締められています。リスク管理を怠らないようご注意ください。",
};

interface VoiceDef {
  voice_id: string;
  voice_name: string;
  lang: "zh" | "en" | "ja";
  desc?: string;
}

const LANG_LABELS: Record<string, string> = {
  zh: "中文",
  en: "英文",
  ja: "日文",
};

function getAudioAccessUrl(filePath: string): string {
  return `http://localhost:8000/files/${filePath}`;
}

function getAudioDownloadUrl(filePath: string): string {
  return `http://localhost:8000/download/${filePath}`;
}

// ── Emotion options ────────────────────────────────────────────────
const EMOTIONS = [
  { value: "", label: "自动" },
  { value: "happy", label: "高兴" },
  { value: "sad", label: "悲伤" },
  { value: "angry", label: "愤怒" },
  { value: "fearful", label: "害怕" },
  { value: "disgusted", label: "厌恶" },
  { value: "surprised", label: "惊讶" },
  { value: "calm", label: "平静" },
  { value: "fluent", label: "生动" },
];

// ── Sound effects ──────────────────────────────────────────────────
const SOUND_EFFECTS = [
  { value: "", label: "无" },
  { value: "spacious_echo", label: "空旷回音" },
  { value: "auditorium_echo", label: "礼堂广播" },
  { value: "lofi_telephone", label: "电话失真" },
  { value: "robotic", label: "电音" },
];

// ── Audio sample rates ─────────────────────────────────────────────
const SAMPLE_RATES = [
  { value: 32000, label: "32000 Hz（高清）" },
  { value: 44100, label: "44100 Hz（CD音质）" },
  { value: 22050, label: "22050 Hz" },
  { value: 16000, label: "16000 Hz" },
  { value: 8000, label: "8000 Hz" },
];

// ── Bitrates ───────────────────────────────────────────────────────
const BITRATES = [
  { value: 128000, label: "128 kbps" },
  { value: 256000, label: "256 kbps" },
  { value: 64000, label: "64 kbps" },
  { value: 32000, label: "32 kbps" },
];

// ── Formats ────────────────────────────────────────────────────────
const AUDIO_FORMATS = [
  { value: "mp3", label: "MP3" },
  { value: "flac", label: "FLAC" },
  { value: "pcm", label: "PCM" },
];

// ── Language boost ────────────────────────────────────────────────
const LANGUAGE_BOOST = [
  { value: "auto", label: "自动检测" },
  { value: "Chinese", label: "中文" },
  { value: "English", label: "英文" },
  { value: "Japanese", label: "日文" },
  { value: "Cantonese", label: "粤语" },
];

export default function VoicePage() {
  const queryClient = useQueryClient();
  const [selectedLang, setSelectedLang] = useState<string>("zh");
  const [previewingId, setPreviewingId] = useState<string | null>(null);
  const [playingId, setPlayingId] = useState<number | null>(null);
  const [pausedId, setPausedId] = useState<number | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [audioTab, setAudioTab] = useState<"preview" | "studio">("preview");
  const [batchGenerating, setBatchGenerating] = useState(false);
  const [batchProgress, setBatchProgress] = useState({ done: 0, total: 0, current: "" });
  const audioRef = useRef<HTMLAudioElement | null>(null);

  const { data: samples = [] } = useQuery({
    queryKey: ["voices", "samples"],
    queryFn: () => voicesApi.list({ limit: 200 }),
  });

  // ── Playback control ────────────────────────────────────────────
  function stopAudio() {
    if (audioRef.current) {
      audioRef.current.pause();
      audioRef.current = null;
    }
    setPlayingId(null);
    setPausedId(null);
  }

  function playOrPause(id: number, url: string) {
    // If this sample is currently playing (not paused), pause it
    if (playingId === id && pausedId === null) {
      audioRef.current?.pause();
      setPausedId(id);
      return;
    }
    // If this sample is paused, resume it
    if (pausedId === id) {
      audioRef.current?.play().catch(() => {});
      setPausedId(null);
      return;
    }
    // Otherwise (different sample or not playing), stop any current and start playing
    stopAudio();
    const audio = new Audio(url);
    audioRef.current = audio;
    setPlayingId(id);
    setPausedId(null);
    audio.onloadedmetadata = () => audio.play().catch(() => { stopAudio(); });
    audio.onended = () => stopAudio();
    audio.onerror = () => stopAudio();
  }

  function toggleFav(sample: VoiceSampleResponse) {
    voicesApi.update(sample.id, { is_favorite: !sample.is_favorite }).then(() => {
      queryClient.invalidateQueries({ queryKey: ["voices", "samples"] });
    });
  }

  // ── Preview voice (existing preview flow) ────────────────────────
  const previewVoice = async (voice: VoiceDef) => {
    if (previewingId) return;

    const existing = samples.find((s) => s.voice_id === voice.voice_id);
    if (existing) {
      playOrPause(existing.id, getAudioAccessUrl(existing.file_path));
      return;
    }

    audioRef.current?.pause();
    setPreviewingId(voice.voice_id);
    setErrorMsg(null);
    try {
      const script = TEST_SCRIPTS[voice.lang] || TEST_SCRIPTS.zh;
      const resp = await fetch("/api/voices/preview", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          voice_id: voice.voice_id,
          voice_name: voice.voice_name,
          lang: voice.lang,
          model: "speech-2.8-hd",
          script_text: script,
        }),
      });
      if (!resp.ok) {
        const err = await resp.json().catch(() => ({}));
        throw new Error(err.detail || `请求失败 ${resp.status}`);
      }
      const data = await resp.json();
      queryClient.invalidateQueries({ queryKey: ["voices", "samples"] });
      if (data.download_url) {
        const audio = new Audio(data.download_url);
        audioRef.current = audio;
        setPlayingId(-1);
        setPausedId(null);
        audio.onloadedmetadata = () => {
          audio.play().catch(() => {
            setErrorMsg("音频播放失败，请稍后重试");
            stopAudio();
          });
        };
        audio.onended = () => stopAudio();
        audio.onerror = () => {
          setErrorMsg("音频播放失败，请稍后重试");
          stopAudio();
        };
      }
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : "未知错误";
      setErrorMsg(msg);
    } finally {
      setPreviewingId(null);
    }
  };

  // ── Batch generate all pending voices ─────────────────────────────
  async function generateAllPending() {
    const pending = SYSTEM_VOICES.filter((v) => !samples.some((s) => s.voice_id === v.voice_id));
    if (pending.length === 0) return;
    setBatchGenerating(true);
    setBatchProgress({ done: 0, total: pending.length, current: pending[0].voice_name });
    for (let i = 0; i < pending.length; i++) {
      const voice = pending[i];
      setBatchProgress((p) => ({ ...p, current: voice.voice_name }));
      let success = false;
      for (let attempt = 0; attempt < 2; attempt++) {
        try {
          const script = TEST_SCRIPTS[voice.lang] || TEST_SCRIPTS.zh;
          const controller = new AbortController();
          const timeout = setTimeout(() => controller.abort(), 180_000); // 3min timeout
          const resp = await fetch("/api/voices/preview", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ voice_id: voice.voice_id, voice_name: voice.voice_name, lang: voice.lang, model: "speech-2.8-hd", script_text: script }),
            signal: controller.signal,
          });
          clearTimeout(timeout);
          if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
          await resp.json().catch(() => {});
          success = true;
          break;
        } catch (err) {
          const isAbort = err instanceof Error && err.name === "AbortError";
          console.warn(`Voice ${voice.voice_id} attempt ${attempt + 1} failed: ${isAbort ? "timeout" : err}`);
          if (attempt === 0) {
            // After first failure, wait before retry (backend may still be processing)
            await new Promise((r) => setTimeout(r, isAbort ? 20_000 : 10_000));
          }
        }
      }
      if (!success) {
        console.error(`Voice ${voice.voice_id} failed after 2 attempts, skipping`);
      }
      setBatchProgress((p) => ({ ...p, done: p.done + 1 }));
      // Delay between voices to avoid rate limit
      await new Promise((r) => setTimeout(r, 800 + Math.random() * 1500));
    }
    await queryClient.invalidateQueries({ queryKey: ["voices", "samples"] });
    setBatchGenerating(false);
    setBatchProgress({ done: 0, total: 0, current: "" });
  }

  // ── Tab button helper ────────────────────────────────────────────
  function TabBtn({ id, label }: { id: "preview" | "studio"; label: string }) {
    const active = audioTab === id;
    return (
      <button
        onClick={() => setAudioTab(id)}
        style={{
          padding: "6px 20px",
          borderRadius: 20,
          border: "1px solid",
          borderColor: active ? "#7b4fc4" : "rgba(200,195,215,0.4)",
          background: active ? "rgba(123,79,196,0.12)" : "rgba(255,255,255,0.5)",
          color: active ? "#7b4fc4" : "#8a8394",
          fontSize: 13,
          fontWeight: 600,
          cursor: "pointer",
        }}
      >
        {label}
      </button>
    );
  }

  return (
    <div>
      {/* 标题 */}
      <div style={{ marginBottom: 20 }}>
        <h2 style={{ fontSize: 22, fontWeight: 700, color: "#3d3545", marginBottom: 8 }}>
          🎙️ 音色管理
        </h2>
        {/* Tab 切换 */}
        <div style={{ display: "flex", gap: 8 }}>
          <TabBtn id="preview" label="音色预览" />
          <TabBtn id="studio" label="音频工坊" />
        </div>
      </div>

      {errorMsg && (
        <div style={{
          background: "rgba(239,68,68,0.1)",
          border: "1px solid rgba(239,68,68,0.3)",
          borderRadius: 10,
          padding: "10px 16px",
          marginBottom: 16,
          fontSize: 13,
          color: "#ef4444",
        }}>
          ⚠️ {errorMsg}
        </div>
      )}

      {audioTab === "preview" ? (
        <VoicePreviewTab
          samples={samples}
          selectedLang={selectedLang}
          setSelectedLang={setSelectedLang}
          previewingId={previewingId}
          playingId={playingId}
          pausedId={pausedId}
          onPreview={previewVoice}
          onPlayOrPause={playOrPause}
          onToggleFav={toggleFav}
          batchGenerating={batchGenerating}
          batchProgress={batchProgress}
          onGenerateAll={generateAllPending}
        />
      ) : (
        <AudioStudioTab
          samples={samples}
          playingId={playingId}
          pausedId={pausedId}
          onPlayOrPause={playOrPause}
          onToggleFav={toggleFav}
        />
      )}
    </div>
  );
}

// ── VoicePreviewTab ─────────────────────────────────────────────────

function VoicePreviewTab({ samples, selectedLang, setSelectedLang, previewingId, playingId, pausedId, onPreview, onPlayOrPause, onToggleFav, batchGenerating, batchProgress, onGenerateAll }: {
  samples: VoiceSampleResponse[];
  selectedLang: string;
  setSelectedLang: (lang: string) => void;
  previewingId: string | null;
  playingId: number | null;
  pausedId: number | null;
  onPreview: (voice: VoiceDef) => void;
  onPlayOrPause: (id: number, url: string) => void;
  onToggleFav: (sample: VoiceSampleResponse) => void;
  batchGenerating: boolean;
  batchProgress: { done: number; total: number; current: string };
  onGenerateAll: () => void;
}) {
  const filteredVoices = selectedLang === "all"
    ? SYSTEM_VOICES
    : SYSTEM_VOICES.filter((v) => v.lang === selectedLang);

  const generatedCount = SYSTEM_VOICES.filter((v) => samples.some((s) => s.voice_id === v.voice_id)).length;
  const pendingCount = SYSTEM_VOICES.length - generatedCount;

  return (
    <div style={{ display: "grid", gridTemplateColumns: "1fr", gap: 24, alignItems: "start" }}>
      {/* 批量生成栏 */}
      <div style={{
        background: "rgba(123,79,196,0.06)",
        border: "1px solid rgba(123,79,196,0.2)",
        borderRadius: 12,
        padding: "12px 16px",
        display: "flex",
        alignItems: "center",
        gap: 16,
        flexWrap: "wrap",
      }}>
        <div style={{ fontSize: 13, color: "#3d3545" }}>
          <span style={{ fontWeight: 600 }}>{generatedCount}</span> / {SYSTEM_VOICES.length} 已生成
          {pendingCount > 0 && <span style={{ color: "#7b4fc4" }}>（{pendingCount} 待生成）</span>}
        </div>
        {batchGenerating ? (
          <div style={{ display: "flex", alignItems: "center", gap: 12, flex: 1 }}>
            <div style={{ flex: 1, height: 6, background: "rgba(123,79,196,0.15)", borderRadius: 3 }}>
              <div style={{
                width: `${(batchProgress.done / batchProgress.total) * 100}%`,
                height: "100%",
                background: "#7b4fc4",
                borderRadius: 3,
                transition: "width 0.3s",
              }} />
            </div>
            <span style={{ fontSize: 12, color: "#7b4fc4", fontWeight: 500, minWidth: 120 }}>
              {batchProgress.done}/{batchProgress.total} · {batchProgress.current}
            </span>
          </div>
        ) : (
          <button
            onClick={onGenerateAll}
            disabled={pendingCount === 0}
            style={{
              padding: "6px 18px",
              borderRadius: 20,
              border: "none",
              background: pendingCount === 0 ? "rgba(123,79,196,0.2)" : "rgba(123,79,196,0.85)",
              color: "#fff",
              fontSize: 12,
              fontWeight: 600,
              cursor: pendingCount === 0 ? "default" : "pointer",
            }}
          >
            🎵 一键生成全部（{pendingCount}）
          </button>
        )}
      </div>

      {/* 语言切换 */}
      <div style={{ display: "flex", gap: 8, marginBottom: 8 }}>
        {[
          { id: "all", label: "全部" },
          { id: "zh", label: "中文" },
          { id: "en", label: "英文" },
          { id: "ja", label: "日文" },
        ].map((l) => (
          <button
            key={l.id}
            onClick={() => setSelectedLang(l.id)}
            style={{
              padding: "6px 18px",
              borderRadius: 20,
              border: "1px solid",
              borderColor: selectedLang === l.id ? "#7b4fc4" : "rgba(200,195,215,0.4)",
              background: selectedLang === l.id ? "rgba(123,79,196,0.12)" : "rgba(255,255,255,0.5)",
              color: selectedLang === l.id ? "#7b4fc4" : "#8a8394",
              fontSize: 13,
              fontWeight: 500,
              cursor: "pointer",
            }}
          >
            {l.label}
            <span style={{
              marginLeft: 5,
              fontSize: 11,
              color: selectedLang === l.id ? "#9b7fd4" : "#c4bfcc",
            }}>
              {l.id === "all" ? SYSTEM_VOICES.length : SYSTEM_VOICES.filter((v) => v.lang === l.id).length}
            </span>
          </button>
        ))}
      </div>

      {/* 音色网格 */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(200px, 1fr))", gap: 10 }}>
        {filteredVoices.map((voice) => {
          const generated = samples.some((s) => s.voice_id === voice.voice_id);
          return (
            <VoiceCard
              key={voice.voice_id}
              voice={voice}
              isPreviewing={previewingId === voice.voice_id}
              generated={generated}
              onPreview={() => onPreview(voice)}
            />
          );
        })}
      </div>
    </div>
  );
}

// ── AudioStudioTab ──────────────────────────────────────────────────

function AudioStudioTab({ samples, playingId, pausedId, onPlayOrPause, onToggleFav }: {
  samples: VoiceSampleResponse[];
  playingId: number | null;
  pausedId: number | null;
  onPlayOrPause: (id: number, url: string) => void;
  onToggleFav: (sample: VoiceSampleResponse) => void;
}) {
  const queryClient = useQueryClient();
  const [generating, setGenerating] = useState(false);
  const [genError, setGenError] = useState<string | null>(null);

  // Form state
  const [text, setText] = useState("欢迎收听本期期货投资教育节目。今日甲醇主力合约稳稳站在2850元附近，核心支撑来自进口端伊朗装置全面停车，5月进口将大幅缩减。");
  const [voiceId, setVoiceId] = useState("Chinese (Mandarin)_Lyrical_Voice");
  const [speed, setSpeed] = useState(1.0);
  const [vol, setVol] = useState(1.0);
  const [pitch, setPitch] = useState(0);
  const [emotion, setEmotion] = useState("");
  const [soundEffect, setSoundEffect] = useState("");
  const [sampleRate, setSampleRate] = useState(32000);
  const [bitrate, setBitrate] = useState(128000);
  const [audioFormat, setAudioFormat] = useState("mp3");
  const [channels, setChannels] = useState(1);
  const [languageBoost, setLanguageBoost] = useState("auto");
  const [pronDict, setPronDict] = useState("");
  const [watermark, setWatermark] = useState(false);

  async function handleGenerate() {
    if (!text.trim()) return;
    setGenerating(true);
    setGenError(null);
    try {
      const params: AudioGenerateParams = {
        text: text.trim(),
        voice_id: voiceId,
        speed,
        vol,
        pitch,
        audio_setting: {
          audio_sample_rate: sampleRate,
          bitrate,
          format: audioFormat,
          channel: channels,
        },
      };
      if (emotion) params.emotion = emotion;
      if (soundEffect) params.voice_modify = { sound_effects: soundEffect };
      if (languageBoost !== "auto") params.language_boost = languageBoost;
      if (pronDict.trim()) {
        const dict: Record<string, string> = {};
        pronDict.split("\n").forEach((line) => {
          const [key, val] = line.split("/").map((s) => s.trim());
          if (key && val) dict[key] = val;
        });
        if (Object.keys(dict).length > 0) params.pronunciation_dict = dict;
      }
      if (watermark) params.aigc_watermark = true;

      await audioApi.generate(params);
      queryClient.invalidateQueries({ queryKey: ["voices", "samples"] });
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : "生成失败";
      setGenError(msg);
    } finally {
      setGenerating(false);
    }
  }

  function handleApplyConfig(params: VoiceSampleResponse["generation_params"]) {
    if (!params) return;
    if (params.speed !== undefined) setSpeed(params.speed);
    if (params.vol !== undefined) setVol(params.vol);
    if (params.pitch !== undefined) setPitch(params.pitch);
    if (params.emotion !== undefined) setEmotion(params.emotion);
    if (params.voice_modify?.sound_effects !== undefined) setSoundEffect(params.voice_modify.sound_effects);
    if (params.audio_setting) {
      if (params.audio_setting.audio_sample_rate !== undefined) setSampleRate(params.audio_setting.audio_sample_rate);
      if (params.audio_setting.bitrate !== undefined) setBitrate(params.audio_setting.bitrate);
      if (params.audio_setting.format !== undefined) setAudioFormat(params.audio_setting.format);
      if (params.audio_setting.channel !== undefined) setChannels(params.audio_setting.channel);
    }
    if (params.language_boost !== undefined) setLanguageBoost(params.language_boost);
  }

  // Filter audio studio history from samples
  const studioSamples = samples.filter((s) => s.notes === "audio_studio" || s.file_path.includes("audio_studio"));

  return (
    <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 24, alignItems: "start" }}>
      {/* 左侧：参数表单 */}
      <div style={{
        background: "rgba(255,255,255,0.75)",
        borderRadius: 14,
        border: "1px solid rgba(200,195,215,0.3)",
        padding: "20px 22px",
      }}>
        <h3 style={{ fontSize: 15, fontWeight: 600, color: "#3d3545", marginBottom: 16 }}>
          🎵 音频生成参数
        </h3>

        {genError && (
          <div style={{ background: "rgba(239,68,68,0.1)", borderRadius: 8, padding: "8px 12px", marginBottom: 12, fontSize: 12, color: "#ef4444" }}>
            ⚠️ {genError}
          </div>
        )}

        <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
          {/* 文本输入 */}
          <div>
            <label style={{ fontSize: 12, color: "#8a8394", marginBottom: 4, display: "block" }}>文本内容</label>
            <textarea
              value={text}
              onChange={(e) => setText(e.target.value)}
              maxLength={50000}
              rows={4}
              style={{
                width: "100%", boxSizing: "border-box",
                border: "1px solid rgba(200,195,215,0.4)",
                borderRadius: 8, padding: "8px 10px",
                fontSize: 13, color: "#3d3545",
                resize: "vertical",
              }}
            />
          </div>

          {/* 音色选择 */}
          <div>
            <label style={{ fontSize: 12, color: "#8a8394", marginBottom: 4, display: "block" }}>音色</label>
            <select
              value={voiceId}
              onChange={(e) => setVoiceId(e.target.value)}
              style={{
                width: "100%", boxSizing: "border-box",
                border: "1px solid rgba(200,195,215,0.4)",
                borderRadius: 8, padding: "6px 10px",
                fontSize: 13, color: "#3d3545",
                background: "#fff",
              }}
            >
              {SYSTEM_VOICES.map((v) => (
                <option key={v.voice_id} value={v.voice_id}>
                  {v.voice_name}（{LANG_LABELS[v.lang] || v.lang}）
                </option>
              ))}
            </select>
          </div>

          {/* 语速 */}
          <SliderField label="语速" value={speed} min={0.5} max={2.0} step={0.1}
            display={`${speed.toFixed(1)}x`}
            onChange={setSpeed} />

          {/* 音量 */}
          <SliderField label="音量" value={vol} min={0.1} max={10} step={0.1}
            display={`${vol.toFixed(1)}`}
            onChange={setVol} />

          {/* 音调 */}
          <SliderField label="音调" value={pitch} min={-12} max={12} step={1}
            display={`${pitch > 0 ? "+" : ""}${pitch}`}
            onChange={setPitch} />

          {/* 情绪 */}
          <div>
            <label style={{ fontSize: 12, color: "#8a8394", marginBottom: 4, display: "block" }}>情绪</label>
            <select
              value={emotion}
              onChange={(e) => setEmotion(e.target.value)}
              style={{
                width: "100%", boxSizing: "border-box",
                border: "1px solid rgba(200,195,215,0.4)",
                borderRadius: 8, padding: "6px 10px",
                fontSize: 13, color: "#3d3545",
                background: "#fff",
              }}
            >
              {EMOTIONS.map((e) => (
                <option key={e.value} value={e.value}>{e.label}</option>
              ))}
            </select>
          </div>

          {/* 音效 */}
          <div>
            <label style={{ fontSize: 12, color: "#8a8394", marginBottom: 4, display: "block" }}>音效</label>
            <select
              value={soundEffect}
              onChange={(e) => setSoundEffect(e.target.value)}
              style={{
                width: "100%", boxSizing: "border-box",
                border: "1px solid rgba(200,195,215,0.4)",
                borderRadius: 8, padding: "6px 10px",
                fontSize: 13, color: "#3d3545",
                background: "#fff",
              }}
            >
              {SOUND_EFFECTS.map((s) => (
                <option key={s.value} value={s.value}>{s.label}</option>
              ))}
            </select>
          </div>

          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10 }}>
            {/* 采样率 */}
            <div>
              <label style={{ fontSize: 12, color: "#8a8394", marginBottom: 4, display: "block" }}>采样率</label>
              <select
                value={sampleRate}
                onChange={(e) => setSampleRate(Number(e.target.value))}
                style={{
                  width: "100%", boxSizing: "border-box",
                  border: "1px solid rgba(200,195,215,0.4)",
                  borderRadius: 8, padding: "6px 8px",
                  fontSize: 12, color: "#3d3545",
                  background: "#fff",
                }}
              >
                {SAMPLE_RATES.map((r) => (
                  <option key={r.value} value={r.value}>{r.label}</option>
                ))}
              </select>
            </div>

            {/* 比特率 */}
            <div>
              <label style={{ fontSize: 12, color: "#8a8394", marginBottom: 4, display: "block" }}>比特率</label>
              <select
                value={bitrate}
                onChange={(e) => setBitrate(Number(e.target.value))}
                style={{
                  width: "100%", boxSizing: "border-box",
                  border: "1px solid rgba(200,195,215,0.4)",
                  borderRadius: 8, padding: "6px 8px",
                  fontSize: 12, color: "#3d3545",
                  background: "#fff",
                }}
              >
                {BITRATES.map((b) => (
                  <option key={b.value} value={b.value}>{b.label}</option>
                ))}
              </select>
            </div>
          </div>

          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10 }}>
            {/* 格式 */}
            <div>
              <label style={{ fontSize: 12, color: "#8a8394", marginBottom: 4, display: "block" }}>格式</label>
              <select
                value={audioFormat}
                onChange={(e) => setAudioFormat(e.target.value)}
                style={{
                  width: "100%", boxSizing: "border-box",
                  border: "1px solid rgba(200,195,215,0.4)",
                  borderRadius: 8, padding: "6px 8px",
                  fontSize: 12, color: "#3d3545",
                  background: "#fff",
                }}
              >
                {AUDIO_FORMATS.map((f) => (
                  <option key={f.value} value={f.value}>{f.label}</option>
                ))}
              </select>
            </div>

            {/* 声道 */}
            <div>
              <label style={{ fontSize: 12, color: "#8a8394", marginBottom: 4, display: "block" }}>声道</label>
              <select
                value={channels}
                onChange={(e) => setChannels(Number(e.target.value))}
                style={{
                  width: "100%", boxSizing: "border-box",
                  border: "1px solid rgba(200,195,215,0.4)",
                  borderRadius: 8, padding: "6px 8px",
                  fontSize: 12, color: "#3d3545",
                  background: "#fff",
                }}
              >
                <option value={1}>单声道</option>
                <option value={2}>双声道</option>
              </select>
            </div>
          </div>

          {/* 语言增强 */}
          <div>
            <label style={{ fontSize: 12, color: "#8a8394", marginBottom: 4, display: "block" }}>语言增强</label>
            <select
              value={languageBoost}
              onChange={(e) => setLanguageBoost(e.target.value)}
              style={{
                width: "100%", boxSizing: "border-box",
                border: "1px solid rgba(200,195,215,0.4)",
                borderRadius: 8, padding: "6px 10px",
                fontSize: 13, color: "#3d3545",
                background: "#fff",
              }}
            >
              {LANGUAGE_BOOST.map((l) => (
                <option key={l.value} value={l.value}>{l.label}</option>
              ))}
            </select>
          </div>

          {/* 发音规则 */}
          <div>
            <label style={{ fontSize: 12, color: "#8a8394", marginBottom: 4, display: "block" }}>发音规则（可选）</label>
            <textarea
              value={pronDict}
              onChange={(e) => setPronDict(e.target.value)}
              placeholder="格式：字/发音&#10;例如：燕少飞/(yan4)(shao3)(fei1)"
              rows={2}
              style={{
                width: "100%", boxSizing: "border-box",
                border: "1px solid rgba(200,195,215,0.4)",
                borderRadius: 8, padding: "6px 10px",
                fontSize: 12, color: "#3d3545",
                resize: "vertical",
              }}
            />
          </div>

          {/* 水印 */}
          <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
            <input
              type="checkbox"
              id="watermark"
              checked={watermark}
              onChange={(e) => setWatermark(e.target.checked)}
            />
            <label htmlFor="watermark" style={{ fontSize: 13, color: "#8a8394", cursor: "pointer" }}>
              添加 AI 水印标识
            </label>
          </div>

          {/* 生成按钮 */}
          <button
            onClick={handleGenerate}
            disabled={generating || !text.trim()}
            style={{
              padding: "10px 20px",
              borderRadius: 10,
              border: "none",
              background: generating ? "rgba(123,79,196,0.3)" : "rgba(123,79,196,0.85)",
              color: "#fff",
              fontSize: 14,
              fontWeight: 600,
              cursor: generating ? "default" : "pointer",
              marginTop: 4,
            }}
          >
            {generating ? "🔊 生成中..." : "🎵 生成音频"}
          </button>
        </div>
      </div>

      {/* 右侧：历史记录 */}
      <div>
        <h3 style={{ fontSize: 15, fontWeight: 600, color: "#3d3545", marginBottom: 12 }}>
          📜 生成历史（{studioSamples.length} 条）
        </h3>
        <div style={{ maxHeight: 500, overflowY: "auto", display: "flex", flexDirection: "column", gap: 8 }}>
          {studioSamples.length === 0 && (
            <div style={{ color: "#bdb9c8", fontSize: 13, textAlign: "center", padding: "30px 0" }}>
              暂无历史记录，请先在左侧生成音频
            </div>
          )}
          {studioSamples.map((sample) => (
            <SampleCard
              key={sample.id}
              sample={sample}
              isPlaying={playingId === sample.id && pausedId === null}
              isPaused={pausedId === sample.id}
              onPlayOrPause={() => onPlayOrPause(sample.id, getAudioAccessUrl(sample.file_path))}
              onToggleFav={() => onToggleFav(sample)}
              onApplyConfig={handleApplyConfig}
            />
          ))}
        </div>
      </div>
    </div>
  );
}

// ── SliderField ───────────────────────────────────────────────────────

function SliderField({ label, value, min, max, step, display, onChange }: {
  label: string; value: number; min: number; max: number; step: number;
  display: string; onChange: (v: number) => void;
}) {
  return (
    <div>
      <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 4 }}>
        <label style={{ fontSize: 12, color: "#8a8394" }}>{label}</label>
        <span style={{ fontSize: 12, color: "#7b4fc4", fontWeight: 600 }}>{display}</span>
      </div>
      <input
        type="range"
        min={min}
        max={max}
        step={step}
        value={value}
        onChange={(e) => onChange(Number(e.target.value))}
        style={{ width: "100%", accentColor: "#7b4fc4" }}
      />
    </div>
  );
}

// ── VoiceCard ─────────────────────────────────────────────────────────

function VoiceCard({ voice, isPreviewing, generated, onPreview }: {
  voice: VoiceDef;
  isPreviewing: boolean;
  generated: boolean;
  onPreview: () => void;
}) {
  const langColor: Record<string, string> = { zh: "#7b4fc4", en: "#3b82f6", ja: "#ef4444" };
  const color = langColor[voice.lang] || "#7b4fc4";

  return (
    <div style={{
      background: "rgba(255,255,255,0.75)",
      borderRadius: 12,
      border: "1px solid rgba(200,195,215,0.3)",
      padding: "12px 14px",
      display: "flex",
      flexDirection: "column",
      gap: 6,
      transition: "all 0.15s",
    }}>
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
        <span style={{ fontSize: 13, fontWeight: 600, color: "#3d3545" }}>{voice.voice_name}</span>
        <div style={{ display: "flex", alignItems: "center", gap: 5 }}>
          {generated && (
            <span style={{
              fontSize: 10,
              background: "rgba(34,197,94,0.12)",
              color: "#22c55e",
              padding: "2px 7px",
              borderRadius: 10,
              fontWeight: 500,
            }}>
              已生成
            </span>
          )}
          <span style={{
            fontSize: 10,
            background: `${color}18`,
            color: color,
            padding: "2px 7px",
            borderRadius: 10,
            fontWeight: 500,
          }}>
            {LANG_LABELS[voice.lang]}
          </span>
        </div>
      </div>
      {voice.desc && (
        <div style={{ fontSize: 11, color: "#8a8394", lineHeight: 1.4 }}>{voice.desc}</div>
      )}
      <div style={{ fontSize: 10, color: "#c4bfcc", fontFamily: "monospace", wordBreak: "break-all" }}>
        {voice.voice_id.length > 38 ? voice.voice_id.slice(0, 38) + "…" : voice.voice_id}
      </div>
      <button
        onClick={onPreview}
        disabled={isPreviewing}
        style={{
          marginTop: 4,
          padding: "5px 14px",
          borderRadius: 8,
          border: "none",
          background: isPreviewing ? "rgba(123,79,196,0.2)" : "rgba(123,79,196,0.15)",
          color: "#7b4fc4",
          fontSize: 12,
          fontWeight: 500,
          cursor: isPreviewing ? "default" : "pointer",
          display: "flex",
          alignItems: "center",
          gap: 5,
        }}
      >
        {isPreviewing ? (
          <><span>🔊</span> 生成中...</>
        ) : (
          <><span>▶</span> 试听</>
        )}
      </button>
    </div>
  );
}

// ── SampleCard ─────────────────────────────────────────────────────────

function SampleCard({ sample, isPlaying, isPaused, onPlayOrPause, onToggleFav, onApplyConfig }: {
  sample: VoiceSampleResponse;
  isPlaying: boolean;
  isPaused: boolean;
  onPlayOrPause: () => void;
  onToggleFav: () => void;
  onApplyConfig: (params: VoiceSampleResponse["generation_params"]) => void;
}) {
  const langColor: Record<string, string> = { zh: "#7b4fc4", en: "#3b82f6", ja: "#ef4444" };
  const color = langColor[sample.lang] || "#7b4fc4";

  const handleDownload = () => {
    const url = getAudioDownloadUrl(sample.file_path);
    const ext = "mp3";
    const defaultName = `${sample.voice_name}_${sample.lang}_${new Date(sample.created_at).toLocaleDateString("zh-CN").replace(/\//g, "-")}.${ext}`;
    const a = document.createElement("a");
    a.href = url;
    a.download = defaultName;
    a.target = "_blank";
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
  };

  return (
    <div style={{
      background: isPlaying ? "rgba(123,79,196,0.08)" : isPaused ? "rgba(123,79,196,0.04)" : "rgba(245,243,238,0.6)",
      borderRadius: 12,
      border: `1px solid ${isPlaying ? "rgba(123,79,196,0.3)" : isPaused ? "rgba(123,79,196,0.2)" : "rgba(200,195,215,0.25)"}`,
      padding: "12px 14px",
    }}>
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 5 }}>
        <div>
          <span style={{ fontSize: 13, fontWeight: 600, color: "#3d3545" }}>{sample.voice_name}</span>
          <span style={{ fontSize: 10, marginLeft: 6, background: `${color}18`, color, padding: "1px 6px", borderRadius: 8 }}>
            {LANG_LABELS[sample.lang] || sample.lang}
          </span>
        </div>
        <button onClick={onToggleFav} style={{ background: "none", border: "none", cursor: "pointer", fontSize: 14 }}>
          {sample.is_favorite ? "⭐" : "☆"}
        </button>
      </div>

      {sample.script_text && (
        <div style={{ display: "flex", alignItems: "flex-start", gap: 6, marginBottom: 6, lineHeight: 1.45 }}>
          <span style={{ fontSize: 11, color: "#8a8394", flex: 1 }}>
            "{sample.script_text.slice(0, 60)}{sample.script_text.length > 60 ? "…" : ""}"
          </span>
          <button
            onClick={() => navigator.clipboard.writeText(sample.script_text)}
            title="复制台词"
            style={{ background: "none", border: "none", cursor: "pointer", fontSize: 11, color: "#7b4fc4", padding: "0 2px" }}
          >📋</button>
        </div>
      )}

      <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
        <button
          onClick={onPlayOrPause}
          style={{
            padding: "4px 12px",
            borderRadius: 8,
            border: "none",
            background: isPlaying ? "#7b4fc4" : isPaused ? "rgba(123,79,196,0.3)" : "rgba(123,79,196,0.15)",
            color: isPlaying || isPaused ? "#fff" : "#7b4fc4",
            fontSize: 12,
            fontWeight: 500,
            cursor: "pointer",
            display: "flex",
            alignItems: "center",
            gap: 4,
          }}
        >
          {isPlaying ? "⏸ 播放中" : isPaused ? "▶ 继续" : "▶ 播放"}
        </button>
        <button onClick={handleDownload} style={{
          padding: "4px 10px",
          borderRadius: 8,
          border: "none",
          background: "rgba(123,79,196,0.1)",
          color: "#7b4fc4",
          fontSize: 12,
          fontWeight: 500,
          cursor: "pointer",
        }}>↓ 下载</button>
        <button onClick={() => onApplyConfig(sample.generation_params)} style={{
          padding: "4px 10px",
          borderRadius: 8,
          border: "none",
          background: "rgba(59,130,246,0.1)",
          color: "#3b82f6",
          fontSize: 12,
          fontWeight: 500,
          cursor: "pointer",
        }}>⚙ 配置应用</button>
        <span style={{ fontSize: 11, color: "#bdb9c8" }}>
          {new Date(sample.created_at).toLocaleDateString("zh-CN")}
        </span>
      </div>
    </div>
  );
}
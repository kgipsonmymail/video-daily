# 普通人版：MiniMax 语音合成（Text to Speech）使用说明

---

## 你能做什么

用 MiniMax 的 API，你可以：

- **把文字变成语音**：输入一段文字，得到一段音频文件
- **用你自己的声音**：录一段音频，上传，API 就能学会你的声音，然后用你的声音读任何文字
- **调节声音效果**：语速快慢、音量大小、音调高低、情绪（高兴/悲伤/平静等）
- **加音效**：回声、电音、电话效果等

---

## 方式一：直接用（系统音色，推荐新手）

### 你需要提供什么（输入）

| 你要填的参数 | 是什么 | 例子 |
|-------------|--------|------|
| `text` | 你想让AI读的文本，最长5万字符 | `"今天天气真好"` |
| `voice_id` | AI 用哪个声音读 | `"Chinese (Mandarin)_Lyrical_Voice"`（见下方列表） |
| `model` | 用哪个模型，固定填 | `"speech-2.8-hd"` |
| `speed` | 语速，0.5~2.0，默认1.0 | `1.0`（正常速度） |
| `vol` | 音量，0~10，默认1.0 | `1.0` |
| `pitch` | 音调，-12~12，0是原音 | `0` |
| `format` | 输出音频格式 | `"mp3"`（最通用） |
| `audio_sample_rate` | 音质，越高越清晰，常用 | `32000` |

### 你会得到什么（输出）

一个 **mp3 音频文件**，直接用播放器就能听。

### 怎么选声音（voice_id 部分示例）

| 声音 | voice_id |
|------|----------|
| 中文温柔女声 | `moss_audio_ce44fc67-7ce3-11f0-8de5-96e35d26fb85` |
| 中文抒情女声 | `Chinese (Mandarin)_Lyrical_Voice` |
| 中文新闻女声 | `Chinese (Mandarin)_News_Anchor` |
| 英文优雅女声 | `English_Graceful_Lady` |
| 英文男声 | `English_Persuasive_Man` |
| 日文低语女声 | `Japanese_Whisper_Belle` |

完整列表调用接口 `POST /v1/get_voice`，传 `{"voice_type": "system"}` 即可查到所有可选声音。

---

## 方式二：克隆你自己的声音（上传录音，API 学你的音色）

适合想让 AI 用**你自己的声音**说话。

### Step 1：你提供一段录音

| 你要做的 | 说明 |
|---------|------|
| 录一段音频 | mp3 / m4a / wav 格式 |
| 时长 | **10秒 ~ 5分钟** |
| 内容 | 随便说什么都行，不用照稿子，清晰即可 |
| 大小 | 不超过 20MB |

> 录音质量越好（安静、无回声、声音清晰），克隆效果越好。

### Step 2：上传录音文件

调用文件上传接口，把录音文件传上去，你会得到一个 `file_id`（一串数字）。

### Step 3：克隆音色

调用克隆接口，填入：
- `file_id`（Step 2 拿到的）
- `voice_id`（你给这个音色起个名字，只能是英文/数字/-/_，首字母必须是英文，末尾不能是 - 或 _，长度8~256）

可选：填 `text` 和 `model`，API 会用你克隆的声音读这段文字返回试听。

### Step 4：等它学会，用起来

克隆完成后（几秒~几十秒），你会得到一个试听链接，听一下是不是你的声音。

**确认是你想要的声音后**，在后续调用 T2S 时，把 `voice_setting.voice_id` 填成你起的那个名字，API 就会用你自己的声音读任何文字了。

> 克隆的音色 **7天内必须用一次**，否则自动删除。

### 可选：提供"示例音频"进一步提升相似度

如果你有一小段（< 8秒）高质量的音频，可以单独上传作为参考（叫"clone_prompt"），帮助 API 更好地还原你的声音。

---

## 方式三：通过文字描述生成新音色

用另一个接口，描述你想要的声音（比如"温柔的30岁女声，略带磁性"），API 会生成一个新的音色 ID，之后用法和上面一样。

---

## 所有可调的参数（普通人版）

### 声音参数（voice_setting）

| 参数 | 你要填什么 | 效果 |
|------|-----------|------|
| `speed` | 0.5 ~ 2.0 | 1.0=正常，2.0=快一倍，0.5=慢一倍 |
| `vol` | 0.1 ~ 10 | 音量大小，1.0=正常 |
| `pitch` | -12 ~ 12 | 音调高低，0=原声，正数偏高，负数偏低 |
| `emotion` | 见下方 | 情绪：happy（高兴）/ sad（悲伤）/ angry（愤怒）/ calm（平静）/ whisper（低语）... |

### 音效参数（voice_modify，后处理）

| 参数 | 你要填什么 | 效果 |
|------|-----------|------|
| `pitch` | -100 ~ 100 | -100=低沉浑厚，+100=清脆明亮 |
| `intensity` | -100 ~ 100 | -100=刚劲有力，+100=轻柔柔和 |
| `timbre` | -100 ~ 100 | -100=磁性厚重，+100=清脆单薄 |
| `sound_effects` | 选一个或留空 | spacious_echo（空旷回音）/ robotic（电音）/ lofi_telephone（电话失真）/ auditorium_echo（礼堂广播）|

### 输出参数（audio_setting）

| 参数 | 你要填什么 | 效果 |
|------|-----------|------|
| `format` | `"mp3"` 或 `"pcm"` 或 `"flac"` | mp3 最通用 |
| `audio_sample_rate` | 32000 或 44100 等 | 44100=CD音质，32000=高清语音，常用32000 |
| `bitrate` | 128000 等 | 越高音质越好，128000够用 |
| `channel` | 1 或 2 | 1=单声道（普通），2=双声道（立体声） |

### 其他

| 参数 | 说明 |
|------|------|
| `text` | 你要让AI读的文本，最长5万字 |
| `pronunciation_dict` | 如果AI读错了某个字的发音，可以手动指定，格式：`"字/(zì)"` |
| `language_boost` | 填 `"auto"` 即可，让AI自动判断语种 |
| `aigc_watermark` | 默认 false，不用改 |

---

## 快速上手示例（最简单用法）

只需要三个参数就能跑起来：

```json
{
  "model": "speech-2.8-hd",
  "text": "今天天气真好，适合出门散步。",
  "voice_setting": {
    "voice_id": "Chinese (Mandarin)_Lyrical_Voice",
    "speed": 1.0
  }
}
```

上传后，你会得到一个 mp3 文件。

---

## 总结

| 场景 | 你要做什么 |
|------|-----------|
| 快速试试 | 选一个系统音色 + 填文字 → 直接出音频 |
| 用自己的声音 | 录10秒~5分钟音频 → 上传 → 克隆 → 用自己声音读任何文字 |
| 精细调音 | 在 voice_setting / voice_modify / audio_setting 里微调各项参数 |

---

> API 地址：`https://api.minimaxi.com/v1/t2a_async_v2`
> 认证方式：Header 传入 `Authorization: Bearer <你的API_KEY>`

T2S HD 调用的是 **异步语音合成接口** `POST /v1/t2a_async_v2`，model 设为 `speech-2.8-hd`（HD 系列最新模型）。

### 基本调用流程

1. **构造请求**，设置 `model: "speech-2.8-hd"`，填入 `text` 和 `voice_setting`
2. **提交任务**，获得 `task_id` 和 `file_id`
3. **轮询任务状态**（`GET /v1/t2a_async_v2`），等待完成
4. **通过 `file_id` 下载音频**（调用文件检索接口）

### 核心请求示例

```
POST https://api.minimaxi.com/v1/t2a_async_v2
Authorization: Bearer <API_KEY>
Content-Type: application/json
```

```json
{
  "model": "speech-2.8-hd",
  "text": "真正的危险不是计算机开始像人一样思考，而是人开始像计算机一样思考。",
  "language_boost": "auto",
  "voice_setting": {
    "voice_id": "moss_audio_ce44fc67-7ce3-11f0-8de5-96e35d26fb85",
    "speed": 1.0,
    "vol": 1.0,
    "pitch": 0
  },
  "audio_setting": {
    "audio_sample_rate": 32000,
    "bitrate": 128000,
    "format": "mp3",
    "channel": 2
  }
}
```

---

## 二、切换音色 / 上传自定义音色

### 方式 1：使用系统音色（直接切换）

在 `voice_setting.voice_id` 中填入系统音色 ID 即可，部分示例：

| 语言 | voice_id | 说明 |
|------|----------|------|
| 中文 | `moss_audio_ce44fc67-7ce3-11f0-8de5-96e35d26fb85` | 标准女声 |
| 中文 | `Chinese (Mandarin)_Lyrical_Voice` | 中文抒情女声 |
| 英文 | `English_Graceful_Lady` | 优雅英女 |
| 英文 | `English_Persuasive_Man` | 有说服力男声 |
| 日文 | `Japanese_Whisper_Belle` | 日文低语女声 |

完整系统音色列表通过 **查询可用音色 API** `POST /v1/get_voice`，传 `voice_type: "system"` 获取。

---

### 方式 2：快速复刻（上传自己的音色）

适合用少量音频（10秒~5分钟）克隆一个真实声音。

**Step 1 — 上传待复刻音频**

```
POST https://api.minimaxi.com/v1/files/upload
Content-Type: multipart/form-data
```

| 字段 | 说明 |
|------|------|
| `purpose` | 固定为 `voice_clone` |
| `file` | 音频文件，mp3/m4a/wav，时长 10秒~5分钟，大小 ≤20MB |

返回 `file_id`（整数）。

**Step 2 — 调用音色复刻接口**

```
POST https://api.minimaxi.com/v1/voice_clone
Content-Type: application/json
```

```json
{
  "file_id": 123456789,
  "voice_id": "MyVoice001",
  "text": "这是一段试听文本，用于预览复刻效果。",
  "model": "speech-2.8-hd",
  "need_noise_reduction": false,
  "need_volume_normalization": false
}
```

> `voice_id` 命名规则：长度 8~256，首字符为英文字母，允许数字/字母/-/_，末尾不可为 - 或 _，不可与已有 ID 重复。

**Step 3 — 激活并使用**

复刻音色需**正式调用一次**后才能通过 `GET /v1/get_voice` 查询到。**7天内未使用会被自动删除**。

**可选：上传示例音频提升相似度**

通过 `POST /v1/files/upload`，purpose 设为 `prompt_audio`（时长<8s），然后在 `voice_clone` 的 `clone_prompt` 中传入 `prompt_audio`（file_id）和 `prompt_text`（对应文本，句末需有标点）。

```json
{
  "file_id": 123456789,
  "voice_id": "MyVoice001",
  "clone_prompt": {
    "prompt_audio": 987654321,
    "prompt_text": "This voice sounds natural and pleasant."
  }
}
```

---

### 方式 3：文生音色（通过文本描述生成音色）

调用 **音色设计接口** `POST /v1/voice_design`，用文本描述生成音色。生成的音色 ID 通过 `POST /v1/get_voice` 传 `voice_type: "voice_generation"` 查询。删除同理传 `voice_type: "voice_generation"` 到删除接口。

---

### 删除音色

```
POST https://api.minimaxi.com/v1/delete_voice
Content-Type: application/json
```

```json
{
  "voice_type": "voice_cloning",
  "voice_id": "MyVoice001"
}
```

> 注意：删除后该 voice_id 不可再用。仅支持删除克隆和文生音色，不支持删除系统音色。

---

## 三、T2S 可控参数完整文档

### 1. `model` — 模型选择

| 可选值 | 说明 |
|--------|------|
| `speech-2.8-hd` | 最新 HD 高质量（推荐） |
| `speech-2.8-turbo` | 最新 Turbo 快速版 |
| `speech-2.6-hd` / `speech-2.6-turbo` | 2.6 系列 |
| `speech-02-hd` / `speech-02-turbo` | 02 系列 |
| `speech-01-hd` / `speech-01-turbo` | 01 系列 |

### 2. `text` — 待合成文本

- 最长 5 万字符
- 与 `text_file_id` 二选一必填
- **语气词标签**（仅 `speech-2.8-hd/turbo` 支持）：

| 标签 | 含义 |
|------|------|
| `(laughs)` | 笑声 |
| `(chuckle)` | 轻笑 |
| `(coughs)` | 咳嗽 |
| `(clear-throat)` | 清嗓子 |
| `(groans)` | 呻吟 |
| `(breath)` | 正常换气 |
| `(pant)` | 喘气 |
| `(inhale)` | 吸气 |
| `(exhale)` | 呼气 |
| `(gasps)` | 倒吸气 |
| `(sniffs)` | 吸鼻子 |
| `(sighs)` | 叹气 |
| `(snorts)` | 喷鼻息 |
| `(burps)` | 打嗝 |
| `(lip-smacking)` | 咂嘴 |
| `(humming)` | 哼唱 |
| `(hissing)` | 嘶嘶声 |
| `(emm)` | 嗯 |
| `(whistles)` | 口哨 |
| `(sneezes)` | 喷嚏 |
| `(crying)` | 抽泣 |
| `(applause)` | 鼓掌 |

### 3. `text_file_id` — 文本文件输入

- 与 `text` 二选一
- 支持 txt、zip
- txt 文件最长 10 万字符，可用 `<#x#>` 标记自定义停顿（x 为秒数，范围 [0.01, 99.99]）
- zip 包内需包含同一格式的 txt 或 json 文件（json 支持 title/content/extra 三个字段）

### 4. `voice_setting` — 音色与声音参数

| 参数 | 范围 | 默认值 | 说明 |
|------|------|--------|------|
| `voice_id` | 字符串 | **必填** | 音色 ID，系统/克隆/文生音色皆可 |
| `speed` | [0.5, 2.0] | 1.0 | 语速，越大越快 |
| `vol` | (0, 10] | 1.0 | 音量，越大越响 |
| `pitch` | [-12, 12] | 0 | 语调，0 为原音 |
| `emotion` | 见下方 | 自动 | 情绪控制 |
| `english_normalization` | true/false | false | 英语数字规范化 |

**emotion 可选值**：

| 值 | 情绪 |
|----|------|
| `happy` | 高兴 |
| `sad` | 悲伤 |
| `angry` | 愤怒 |
| `fearful` | 害怕 |
| `disgusted` | 厌恶 |
| `surprised` | 惊讶 |
| `calm` | 中性 |
| `fluent` | 生动 |
| `whisper` | 低语 |

> 注意：`fluent` 和 `whisper` 仅 `speech-2.6-hd/turbo` 支持；`speech-2.8-hd/turbo` 不支持 `whisper`。

### 5. `voice_modify` — 声音效果器（后处理）

| 参数 | 范围 | 说明 |
|------|------|------|
| `pitch` | [-100, 100] | -100=低沉，+100=明亮 |
| `intensity` | [-100, 100] | -100=刚劲，+100=柔和 |
| `timbre` | [-100, 100] | -100=浑厚，+100=清脆 |
| `sound_effects` | 见下方 | 音效 |

**sound_effects 可选值**：

| 值 | 音效 |
|----|------|
| `spacious_echo` | 空旷回音 |
| `auditorium_echo` | 礼堂广播 |
| `lofi_telephone` | 电话失真 |
| `robotic` | 电音 |

### 6. `audio_setting` — 音频输出参数

| 参数 | 可选值 | 默认值 |
|------|--------|--------|
| `audio_sample_rate` | 8000, 16000, 22050, 24000, 32000, 44100 | 32000 |
| `bitrate` | 32000, 64000, 128000, 256000 | 128000（仅 mp3 生效） |
| `format` | `mp3`, `pcm`, `flac` | `mp3` |
| `channel` | 1（单声道）, 2（双声道） | 1 |

### 7. `pronunciation_dict` — 发音规则

通过 `tone` 数组指定"文字→注音/替代发音"规则，中文声调用数字表示（1=一声, 2=二声, 3=三声, 4=四声, 5=轻声）。

```json
{
  "pronunciation_dict": {
    "tone": [
      "燕少飞/(yan4)(shao3)(fei1)",
      "omg/oh my god"
    ]
  }
}
```

### 8. `language_boost` — 小语种增强

设为 `auto` 让模型自主判断语种。可选值：Chinese, Chinese,Yue, English, Arabic, Russian, Spanish, French, Portuguese, German, Turkish, Dutch, Ukrainian, Vietnamese, Indonesian, Japanese, Italian, Korean, Thai, Polish, Romanian, Greek, Czech, Finnish, Hindi, Bulgarian, Danish, Hebrew, Malay, Persian, Slovak, Swedish, Croatian, Filipino, Hungarian, Norwegian, Slovenian, Catalan, Nynorsk, Tamil, Afrikaans, auto。

> 注意：speech-01/02 系列不支持 Persian、Filipino、Tamil。

### 9. `aigc_watermark` — AI标识

`true` 在音频末尾添加节奏标识（默认 false，仅非流式合成生效）。

---

## 四、总结：使用路径

```
选音色
  └── system（直接用系统音色）
  └── voice_cloning（上传音频克隆）
  └── voice_generation（文生音色）
      │
      ├── voice_id → voice_setting.voice_id
      │
调声音参数
  ├── speed / vol / pitch
  └── emotion（情绪）
      │
调音效（voice_modify）
  ├── pitch / intensity / timbre
  └── sound_effects
      │
调输出格式
  └── audio_setting（采样率/比特率/格式/声道）
      │
提交合成 → 轮询任务状态 → 下载音频
```

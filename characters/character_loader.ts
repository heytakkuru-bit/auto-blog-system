/**
 * character_loader.ts
 * サキ・ハル両キャラクターを管理し、Claude API の system prompt に注入するモジュール
 */

import sakiData from "./character_saki.json";
import haruData from "./character_haru.json";

// ─── 型定義 ────────────────────────────────────────────────────

export type CharacterId = "saki" | "haru";
export type VariantId = "A" | "B";
export type ClosingPattern = "A" | "B" | "C" | "D" | "E";

export interface CharacterMeta {
  version: string;
  character_id: CharacterId;
  target_gender: "male" | "female";
  created_at: string;
  description: string;
}

export interface SpeechVariant {
  label: string;
  sentence_endings: string[];
  line_length: string;
  emoji_policy: string;
  pause_usage: string;
  question_style: string;
  tone_sample: string;
}

export interface ContentTemplates {
  tiktok_x: {
    admiration: string[];
    empathy: string[];
    knowledge: string[];
    change: string[];
    provocation: string[];
  };
}

export interface LineMessage {
  purpose: string;
  message: string;
}

export interface ReplyPattern {
  situation: string;
  template: string;
}

export interface ClosingMessage {
  pattern: ClosingPattern;
  label: string;
  message: string;
}

export interface Character {
  meta: CharacterMeta;
  profile: Record<string, unknown>;
  personality: {
    core_traits: string[];
    values: string[];
    forbidden_behaviors: string[];
  };
  speech_rules: {
    primary_variant: VariantId;
    variants: Record<VariantId, SpeechVariant>;
  };
  content_templates: ContentTemplates;
  line_messages: Record<string, LineMessage>;
  reply_patterns: ReplyPattern[];
  closing_messages: ClosingMessage[];
  system_prompt_template: string;
}

// ─── キャラクター取得 ────────────────────────────────────────────

const CHARACTERS: Record<CharacterId, Character> = {
  saki: sakiData as Character,
  haru: haruData as Character,
};

/**
 * キャラクターを取得する
 */
export function getCharacter(id: CharacterId): Character {
  const char = CHARACTERS[id];
  if (!char) throw new Error(`Character not found: ${id}`);
  return char;
}

/**
 * ターゲット性別からキャラクターを取得する
 */
export function getCharacterByTargetGender(
  gender: "male" | "female"
): Character {
  const entry = Object.values(CHARACTERS).find(
    (c) => c.meta.target_gender === gender
  );
  if (!entry) throw new Error(`No character found for gender: ${gender}`);
  return entry;
}

// ─── System Prompt 生成 ────────────────────────────────────────────

export interface BuildSystemPromptOptions {
  characterId: CharacterId;
  variant?: VariantId;
  includeValues?: boolean;
  includeReplyPatterns?: boolean;
  includeClosingPatterns?: ClosingPattern[];
}

/**
 * Claude API の system prompt を構築する
 */
export function buildSystemPrompt(options: BuildSystemPromptOptions): string {
  const {
    characterId,
    variant,
    includeValues = true,
    includeReplyPatterns = false,
    includeClosingPatterns,
  } = options;

  const char = getCharacter(characterId);
  const activeVariant = variant ?? char.speech_rules.primary_variant;
  const variantData = char.speech_rules.variants[activeVariant];

  const sections: string[] = [char.system_prompt_template];

  if (includeValues) {
    sections.push(
      `\n【価値観・信条】\n` + char.personality.values.map((v) => `- ${v}`).join("\n")
    );
  }

  sections.push(
    `\n【現在の文体バリアント: ${activeVariant} - ${variantData.label}】\n` +
      `語尾例: ${variantData.sentence_endings.join(" / ")}\n` +
      `絵文字: ${variantData.emoji_policy}\n` +
      `文長: ${variantData.line_length}`
  );

  if (includeReplyPatterns && char.reply_patterns.length > 0) {
    const patterns = char.reply_patterns
      .map((p) => `[${p.situation}]\n${p.template}`)
      .join("\n\n");
    sections.push(`\n【返信パターン例】\n${patterns}`);
  }

  if (includeClosingPatterns && includeClosingPatterns.length > 0) {
    const closings = char.closing_messages
      .filter((c) => includeClosingPatterns.includes(c.pattern))
      .map((c) => `[${c.label}]\n${c.message}`)
      .join("\n\n");
    sections.push(`\n【クロージング文例】\n${closings}`);
  }

  return sections.join("\n");
}

// ─── コンテンツ取得ユーティリティ ────────────────────────────────────

/**
 * 投稿テンプレートをランダムまたはインデックス指定で取得する
 */
export function getPostTemplate(
  characterId: CharacterId,
  category: keyof ContentTemplates["tiktok_x"],
  index?: number
): string {
  const char = getCharacter(characterId);
  const templates = char.content_templates.tiktok_x[category];
  const i = index !== undefined ? index % templates.length : Math.floor(Math.random() * templates.length);
  return templates[i];
}

/**
 * LINE メッセージを日数で取得する
 */
export function getLineMessage(
  characterId: CharacterId,
  day: number
): LineMessage {
  const char = getCharacter(characterId);
  const key = `day${day}`;
  const msg = char.line_messages[key];
  if (!msg) throw new Error(`Line message not found: day${day}`);
  return msg;
}

/**
 * シチュエーションに最も近い返信パターンを取得する（部分一致）
 */
export function findReplyPattern(
  characterId: CharacterId,
  situationKeyword: string
): ReplyPattern | undefined {
  const char = getCharacter(characterId);
  return char.reply_patterns.find((p) =>
    p.situation.includes(situationKeyword)
  );
}

/**
 * クロージングメッセージをパターン指定で取得する
 */
export function getClosingMessage(
  characterId: CharacterId,
  pattern: ClosingPattern
): ClosingMessage {
  const char = getCharacter(characterId);
  const msg = char.closing_messages.find((c) => c.pattern === pattern);
  if (!msg) throw new Error(`Closing pattern not found: ${pattern}`);
  return msg;
}

// ─── A/B テストユーティリティ ────────────────────────────────────────

/**
 * ユーザーIDをもとに A/B バリアントを決定する（50/50 分割）
 */
export function resolveVariant(userId: string): VariantId {
  const hash = userId.split("").reduce((acc, c) => acc + c.charCodeAt(0), 0);
  return hash % 2 === 0 ? "A" : "B";
}

/**
 * A/B テスト用の system prompt を生成する
 */
export function buildSystemPromptForUser(
  characterId: CharacterId,
  userId: string,
  options?: Omit<BuildSystemPromptOptions, "characterId" | "variant">
): { prompt: string; variant: VariantId } {
  const variant = resolveVariant(userId);
  const prompt = buildSystemPrompt({ characterId, variant, ...options });
  return { prompt, variant };
}

// ─── メタ情報 ────────────────────────────────────────────────────

/**
 * 全キャラクターのメタ情報一覧を取得する
 */
export function listCharacters(): CharacterMeta[] {
  return Object.values(CHARACTERS).map((c) => c.meta);
}

/**
 * キャラクターのバージョンを確認する
 */
export function getVersion(characterId: CharacterId): string {
  return getCharacter(characterId).meta.version;
}

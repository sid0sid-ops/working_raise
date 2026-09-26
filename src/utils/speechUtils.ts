export function computeVoiceWaveScale(
  level: number,
  isVoiceSpeaking: boolean,
  barIndex: number
): number {
  if (isVoiceSpeaking) {
    return Math.max(level, 0.75 + (barIndex % 3) * 0.4);
  }
  return Math.min(level, 0.35);
}

export const cleanTextForSpeech = (text: string): string => {
  return text
    .replace(/```[\s\S]*?```/g, 'Code block omitted.')
    .replace(/`([^`]+)`/g, '$1')
    .replace(/\[\^?\d+\]/g, '')
    .replace(/[#*_~>]/g, '')
    .replace(/\s+/g, ' ')
    .trim();
};

export const ROBOTIC_VOICE_NAMES = [
  'albert',
  'bad news',
  'bahh',
  'bells',
  'boing',
  'bubbles',
  'cellos',
  'deranged',
  'good news',
  'hysterical',
  'pipe organ',
  'organ',
  'trinoids',
  'whisper',
  'wobble',
  'zarvox',
  'fred',
  'junior',
  'ralph',
  'superstar',
  'jester',
];

export const filterNaturalVoices = <T extends { name: string; lang: string }>(voices: T[]): T[] => {
  return voices.filter((v) => {
    const isEnglish = v.lang.toLowerCase().startsWith('en');
    const isRobotic = ROBOTIC_VOICE_NAMES.some((rob) => v.name.toLowerCase().includes(rob));
    return isEnglish && !isRobotic;
  });
};

export const selectBestSpeechVoice = <T extends { name: string; lang: string }>(
  voices: T[],
  preferredVoiceName?: string | null
): T | null => {
  if (!voices || voices.length === 0) return null;

  // 1. If preferred voice is specified and exists, use it
  if (preferredVoiceName) {
    const userChoice = voices.find((v) => v.name === preferredVoiceName);
    if (userChoice) return userChoice;
  }

  // 2. Filter out novelty/robotic legacy synthesizers
  const natural = filterNaturalVoices(voices);
  const pool = natural.length > 0 ? natural : voices;

  // 3. Priority to Enhanced, Premium, Neural, Natural modern voices
  const premium = pool.find((v) => {
    const n = v.name.toLowerCase();
    return (
      n.includes('enhanced') ||
      n.includes('premium') ||
      n.includes('natural') ||
      n.includes('neural') ||
      n.includes('online')
    );
  });
  if (premium) return premium;

  // 4. Well-known high-fidelity assistant voices
  const preferredPriority = [
    'samantha',
    'google uk english female',
    'google us english',
    'daniel',
    'karen',
    'ava',
    'serena',
    'reed',
    'flo',
    'sandy',
    'shelley',
    'alex',
  ];

  for (const name of preferredPriority) {
    const found = pool.find((v) => v.name.toLowerCase().includes(name));
    if (found) return found;
  }

  // 5. Default to any en-US or English voice in the pool
  return (
    pool.find((v) => v.lang === 'en-US') ||
    pool.find((v) => v.lang.toLowerCase().startsWith('en')) ||
    pool[0]
  );
};

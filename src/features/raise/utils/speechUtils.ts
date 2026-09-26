import type { ChatMessage, QuestionVersion, ResponseVersion } from '../../../types';

export {
  cleanTextForSpeech,
  computeVoiceWaveScale,
  filterNaturalVoices,
  ROBOTIC_VOICE_NAMES,
  selectBestSpeechVoice,
} from '../../../utils/speechUtils';

export const getTurnQuestionVersions = (
  userMsg: ChatMessage,
  assistantMsg?: ChatMessage
): QuestionVersion[] => {
  if (userMsg.questionVersions && userMsg.questionVersions.length > 0) {
    return userMsg.questionVersions;
  }
  const initialResp: ResponseVersion = {
    id: `resp-init-${Date.now()}`,
    text: assistantMsg && assistantMsg.role === 'assistant' ? assistantMsg.text : '',
    response: assistantMsg && assistantMsg.role === 'assistant' ? assistantMsg.response : undefined,
    timestamp: 'Original',
  };
  return [
    {
      id: `qver-init-${Date.now()}`,
      question: userMsg.text,
      responseVersions: initialResp.text ? [initialResp] : [],
      currentResponseVersionIndex: 0,
      timestamp: 'Original',
    },
  ];
};

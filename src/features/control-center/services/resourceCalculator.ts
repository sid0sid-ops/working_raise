import type { ControlCenterConfig } from '../types';

export interface AddedSubstrate {
  category: 'Platform' | 'Inference' | 'Knowledge Graph' | 'Storage' | 'Cache';
  label: string;
  diskGb: number;
  ramGb: number;
  isCloud: boolean;
}

export interface ResourceFootprint {
  totalDiskGb: number;
  totalRamGb: number;
  estimatedTime: string;
  addedSubstrates: AddedSubstrate[];
}

export const calculateResourceFootprint = (config: ControlCenterConfig): ResourceFootprint => {
  let totalDiskGb = 0;
  let totalRamGb = 1.2; // Base RAISE workstation memory footprint
  const addedSubstrates: AddedSubstrate[] = [];

  // 1. Platform substrate
  addedSubstrates.push({
    category: 'Platform',
    label: config.targetPlatform.toUpperCase(),
    diskGb: 0,
    ramGb: 0,
    isCloud: false,
  });

  // 2. Intelligence Engine (Cloud vs Local)
  if (config.llmMode === 'cloud_groq') {
    addedSubstrates.push({
      category: 'Inference',
      label: 'Groq LPU (Llama 3.3 70B)',
      diskGb: 0,
      ramGb: 0,
      isCloud: true,
    });
  } else if (config.llmMode === 'cloud_gemini') {
    addedSubstrates.push({
      category: 'Inference',
      label: 'Google Gemini 2.5 Flash',
      diskGb: 0,
      ramGb: 0,
      isCloud: true,
    });
  } else {
    const localModelMap: Record<string, { label: string; disk: number; ram: number }> = {
      'llama3.2:3b': { label: 'Llama 3.2 3B', disk: 2.0, ram: 4.0 },
      'qwen2.5:7b': { label: 'Qwen 2.5 7B', disk: 4.7, ram: 8.0 },
      'llama3.1:8b': { label: 'Llama 3.1 8B', disk: 4.9, ram: 8.0 },
    };
    const model = localModelMap[config.selectedLocalModel] || {
      label: config.selectedLocalModel,
      disk: 2.0,
      ram: 4.0,
    };
    totalDiskGb += model.disk;
    totalRamGb += model.ram;
    addedSubstrates.push({
      category: 'Inference',
      label: model.label,
      diskGb: model.disk,
      ramGb: model.ram,
      isCloud: false,
    });
  }

  // 3. Knowledge Graph Substrate (Neo4j)
  if (config.neo4jMode === 'local') {
    totalDiskGb += 1.5;
    totalRamGb += 0.5;
    addedSubstrates.push({
      category: 'Knowledge Graph',
      label: 'Local Neo4j Bolt',
      diskGb: 1.5,
      ramGb: 0.5,
      isCloud: false,
    });
  } else if (config.neo4jMode === 'cloud') {
    addedSubstrates.push({
      category: 'Knowledge Graph',
      label: 'Neo4j AuraDB Cloud',
      diskGb: 0,
      ramGb: 0,
      isCloud: true,
    });
  } else {
    addedSubstrates.push({
      category: 'Knowledge Graph',
      label: 'Vector Search Fallback',
      diskGb: 0,
      ramGb: 0,
      isCloud: false,
    });
  }

  // 4. Persistence & Cache Substrates
  if (config.postgresMode === 'cloud') {
    addedSubstrates.push({
      category: 'Storage',
      label: 'Cloud Neon Postgres',
      diskGb: 0,
      ramGb: 0,
      isCloud: true,
    });
  } else {
    addedSubstrates.push({
      category: 'Storage',
      label: 'In-Memory Sessions',
      diskGb: 0,
      ramGb: 0,
      isCloud: false,
    });
  }

  if (config.redisMode === 'cloud') {
    addedSubstrates.push({
      category: 'Cache',
      label: 'Cloud Upstash Redis',
      diskGb: 0,
      ramGb: 0,
      isCloud: true,
    });
  } else {
    addedSubstrates.push({
      category: 'Cache',
      label: 'In-Memory Cache',
      diskGb: 0,
      ramGb: 0,
      isCloud: false,
    });
  }

  // Estimated Setup Time calculation
  let estimatedTime = 'Instant (~15 seconds)';
  if (totalDiskGb >= 4.0) {
    estimatedTime = '~3 – 5 min download';
  } else if (totalDiskGb > 0) {
    estimatedTime = '~1 – 2 min download';
  }

  return {
    totalDiskGb: Math.round(totalDiskGb * 10) / 10,
    totalRamGb: Math.round(totalRamGb * 10) / 10,
    estimatedTime,
    addedSubstrates,
  };
};

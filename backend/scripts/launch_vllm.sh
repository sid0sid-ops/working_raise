export VLLM_USE_V1=0

python3 -m vllm.entrypoints.openai.api_server \
    --model Qwen/Qwen2.5-14B-Instruct-GPTQ-Int4 \
    --host 0.0.0.0 \
    --port 8000 \
    --quantization gptq \
    --max-model-len 8192 \
    --gpu-memory-utilization 0.55 \
    --enable-prefix-caching \
    --trust-remote-code \
    --tensor-parallel-size 1

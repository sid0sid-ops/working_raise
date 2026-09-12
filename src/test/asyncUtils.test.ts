import { describe, it, expect } from 'vitest';
import { ensureMinimumDuration } from '../utils/async';

describe('ensureMinimumDuration', () => {
  it('waits at least the specified minimum time for fast tasks', async () => {
    const start = Date.now();
    const fastTask = Promise.resolve('fast result');

    const result = await ensureMinimumDuration(fastTask, 200);
    const elapsed = Date.now() - start;

    expect(result).toBe('fast result');
    expect(elapsed).toBeGreaterThanOrEqual(180); // within tolerance
  });

  it('resolves as soon as a slow task finishes if it exceeds minMs', async () => {
    const start = Date.now();
    const slowTask = new Promise<string>((resolve) => setTimeout(() => resolve('slow result'), 300));

    const result = await ensureMinimumDuration(slowTask, 100);
    const elapsed = Date.now() - start;

    expect(result).toBe('slow result');
    expect(elapsed).toBeGreaterThanOrEqual(280);
  });

  it('aborts early without waiting if AbortSignal is triggered', async () => {
    const controller = new AbortController();
    const start = Date.now();

    // Trigger abort after 50ms
    setTimeout(() => controller.abort(), 50);

    const task = new Promise<string>((_, reject) => {
      controller.signal.addEventListener('abort', () => {
        reject(new Error('Aborted'));
      });
    });

    await expect(ensureMinimumDuration(task, 1000, controller.signal)).rejects.toThrow('Aborted');
    const elapsed = Date.now() - start;
    expect(elapsed).toBeLessThan(300);
  });

  it('waits minimum duration on task failure unless aborted', async () => {
    const start = Date.now();
    const failingTask = Promise.reject(new Error('Backend error'));

    await expect(ensureMinimumDuration(failingTask, 200)).rejects.toThrow('Backend error');
    const elapsed = Date.now() - start;
    expect(elapsed).toBeGreaterThanOrEqual(180);
  });
});

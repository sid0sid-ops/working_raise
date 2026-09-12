/**
 * Ensures that an asynchronous task takes at least `minMs` milliseconds before completing.
 * - If the task completes faster (e.g. mock mode or quick cache), it waits out the remaining duration so the user sees thinking thoughts.
 * - If the task takes longer (e.g. when real backend processes user documents), it naturally resolves as soon as the task completes.
 * - If the task errors out, it still respects the minimum duration unless aborted.
 * - If `signal` is aborted (user clicks 'Stop Generating'), it resolves immediately without delay.
 */
export async function ensureMinimumDuration<T>(
  task: Promise<T>,
  minMs: number = 2000,
  signal?: AbortSignal
): Promise<T> {
  const minDelay = new Promise<void>((resolve) => {
    if (signal?.aborted) {
      resolve();
      return;
    }
    const timer = setTimeout(resolve, minMs);
    signal?.addEventListener(
      'abort',
      () => {
        clearTimeout(timer);
        resolve();
      },
      { once: true }
    );
  });

  let errorToThrow: any = null;
  let hasError = false;

  const wrappedTask = task
    .then((val) => val)
    .catch((err) => {
      hasError = true;
      errorToThrow = err;
      return undefined as unknown as T;
    });

  const [result] = await Promise.all([wrappedTask, minDelay]);

  if (hasError) {
    throw errorToThrow;
  }

  return result;
}

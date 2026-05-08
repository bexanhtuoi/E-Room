import { useEffect, useState } from 'react';

export function useAsyncResource(loader, initialValue) {
  const [data, setData] = useState(initialValue);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    let isActive = true;

    async function run() {
      setIsLoading(true);
      setError('');

      try {
        const result = await loader();
        if (isActive) {
          setData(result);
        }
      } catch (caughtError) {
        if (isActive) {
          setError(caughtError instanceof Error ? caughtError.message : 'Unknown error');
        }
      } finally {
        if (isActive) {
          setIsLoading(false);
        }
      }
    }

    run();

    return () => {
      isActive = false;
    };
  }, [loader]);

  return { data, isLoading, error };
}

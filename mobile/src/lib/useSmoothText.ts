import { useEffect, useRef, useState } from 'react';

// at least this many characters a frame, more when far behind
const MIN_STEP = 2;
const CATCH_UP = 6;

// The reply arrives in uneven chunks; this lets it out at an even pace, a
// few words a frame, speeding up when it falls behind, so the text flows
// instead of jumping. Stops on a word's end so words don't appear in halves.
export function useSmoothText(target: string): string {
  const [shown, setShown] = useState(0);
  const length = useRef(0);

  useEffect(() => {
    // a new reply, or the text was replaced
    if (length.current > target.length) {
      length.current = 0;
      setShown(0);
    }
    let frame = 0;
    const tick = () => {
      const behind = target.length - length.current;
      if (behind <= 0) return;
      let next = length.current + Math.max(MIN_STEP, Math.ceil(behind / CATCH_UP));
      const space = target.indexOf(' ', next);
      next = space === -1 ? target.length : Math.min(space, target.length);
      length.current = next;
      setShown(next);
      frame = requestAnimationFrame(tick);
    };
    frame = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(frame);
  }, [target]);

  return target.slice(0, shown);
}

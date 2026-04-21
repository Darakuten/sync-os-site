(() => {
  const clamp01 = (v) => Math.max(0, Math.min(1, v));
  const norm = (v, lo, hi) => clamp01((v - lo) / Math.max(1e-6, hi - lo));

  class SmoothedScore {
    constructor(initial = 0.5, alpha = 0.18) {
      this.value = initial;
      this.alpha = alpha;
      this.history = Array.from({ length: 90 }, () => initial);
    }
    step(target) {
      this.value += (target - this.value) * this.alpha;
      this.history.push(this.value);
      if (this.history.length > 90) this.history.shift();
      return this.value;
    }
  }

  const smoothers = {
    stress: new SmoothedScore(0.35),
    emotion: new SmoothedScore(0.6),
    fatigue: new SmoothedScore(0.3),
    attention: new SmoothedScore(0.7),
    cogload: new SmoothedScore(0.45),
  };

  const LABELS = {
    stress: "acute",
    emotion: "valence",
    fatigue: "mental",
    attention: "focus",
    cogload: "n-back eq.",
  };

  const ATTRIBUTIONS = {
    stress: ["LF/HF", "SCR", "HR"],
    emotion: ["α power", "blink"],
    fatigue: ["α/β", "RR", "HR"],
    attention: ["β power", "α/β", "blink"],
    cogload: ["β power", "HR", "LF/HF"],
  };

  const ACCENTS = {
    stress: "#ff8a4c",
    emotion: "#ff4e7d",
    fatigue: "#ff6b4a",
    attention: "#7df9ff",
    cogload: "#b4e23f",
  };

  function computeConstructs(kpisMap) {
    const hr = kpisMap.ecg?.hr ?? kpisMap.ppg?.hr ?? 72;
    const lfhf = kpisMap.ecg?.lfhf ?? 1.5;
    const scr = kpisMap.eda?.scr ?? 2.0;
    const alpha = kpisMap.eeg?.alpha ?? 25;
    const beta = kpisMap.eeg?.beta ?? 15;
    const abRatio = kpisMap.eeg?.ab_ratio ?? 1.6;
    const blink = kpisMap.eye?.blink ?? 14;
    const hrvLike = 1 / Math.max(0.4, lfhf);
    const rr = kpisMap.resp?.rr ?? 14;

    const targets = {
      stress: clamp01(0.45 * norm(lfhf, 0.8, 4.8) + 0.35 * norm(scr, 0.5, 8.0) + 0.20 * norm(hr, 62, 105)),
      emotion: clamp01(0.60 * norm(alpha, 8, 55) + 0.40 * (1 - norm(blink, 8, 35))),
      fatigue: clamp01(0.45 * (1 - norm(abRatio, 0.6, 2.6)) + 0.30 * norm(rr, 8, 26) + 0.25 * norm(hr, 55, 95)),
      attention: clamp01(0.45 * norm(beta, 6, 35) + 0.30 * norm(abRatio, 0.8, 2.4) + 0.25 * (1 - norm(blink, 8, 28))),
      cogload: clamp01(0.35 * norm(beta, 10, 35) + 0.30 * norm(hr, 60, 110) + 0.20 * norm(lfhf, 0.8, 4.8) + 0.15 * (1 - norm(hrvLike, 0.2, 1.2))),
    };

    const scores = {};
    Object.keys(smoothers).forEach((key) => {
      scores[key] = {
        id: key,
        label: key.toUpperCase(),
        tag: LABELS[key],
        value: smoothers[key].step(targets[key]),
        history: [...smoothers[key].history],
        attribution: ATTRIBUTIONS[key],
        accent: ACCENTS[key],
      };
    });
    return scores;
  }

  window.ConstructEngine = {
    computeConstructs,
  };
})();

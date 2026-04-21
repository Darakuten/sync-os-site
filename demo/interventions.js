(() => {
  const INTERVENTIONS = [
    { id: "vns", label: "VNS", category: "electric", min: 0, max: 5, unit: "mA", defaultValue: 1.2, impacts: { stress: -0.12, attention: 0.08 } },
    { id: "tdcs", label: "tDCS", category: "electric", min: 0, max: 3, unit: "mA", defaultValue: 0.8, impacts: { attention: 0.12, cogload: 0.06 } },
    { id: "tens", label: "TENS", category: "electric", min: 0, max: 6, unit: "mA", defaultValue: 1.5, impacts: { stress: -0.08, fatigue: -0.06 } },
    { id: "haptic_wrist", label: "Haptic Wrist", category: "vibration", min: 20, max: 240, unit: "Hz", defaultValue: 80, impacts: { stress: -0.07, emotion: 0.04 } },
    { id: "haptic_chest", label: "Haptic Chest", category: "vibration", min: 20, max: 180, unit: "Hz", defaultValue: 60, impacts: { stress: -0.06, fatigue: -0.04 } },
    { id: "hrv_sync", label: "HRV Sync", category: "vibration", min: 0, max: 100, unit: "%", defaultValue: 55, impacts: { stress: -0.10, emotion: 0.06 } },
    { id: "binaural", label: "Binaural 40Hz", category: "audio", min: 0, max: 100, unit: "%", defaultValue: 35, impacts: { attention: 0.10, emotion: 0.05 } },
    { id: "whitenoise", label: "White Noise", category: "audio", min: 0, max: 100, unit: "%", defaultValue: 20, impacts: { cogload: -0.06, stress: -0.04 } },
    { id: "naturesound", label: "Nature Sound", category: "audio", min: 0, max: 100, unit: "%", defaultValue: 30, impacts: { emotion: 0.10, stress: -0.06 } },
    { id: "amber620", label: "Amber 620nm", category: "light", min: 0, max: 100, unit: "%", defaultValue: 45, impacts: { emotion: 0.09, fatigue: -0.05 } },
    { id: "circadian", label: "Circadian Mode", category: "light", min: 0, max: 100, unit: "%", defaultValue: 40, impacts: { fatigue: -0.08, stress: -0.04 } },
    { id: "pulse_light", label: "Pulse Light", category: "light", min: 1, max: 30, unit: "Hz", defaultValue: 8, impacts: { attention: 0.07, cogload: 0.04 } },
    { id: "aroma", label: "Aroma Diffuser", category: "pseudo", min: 0, max: 100, unit: "%", defaultValue: 25, impacts: { emotion: 0.11, stress: -0.05 } },
    { id: "taste_elec", label: "Taste Stim", category: "pseudo", min: 0, max: 100, unit: "%", defaultValue: 18, impacts: { attention: 0.05, emotion: 0.04 } },
  ];

  const CATEGORY_LABELS = {
    electric: "電気",
    vibration: "振動",
    audio: "音響",
    light: "光",
    pseudo: "疑似五感",
  };

  const CATEGORY_ACCENTS = {
    electric: "#ff8a4c",
    vibration: "#ffd166",
    audio: "#7df9ff",
    light: "#b4e23f",
    pseudo: "#ff4e7d",
  };

  const PRESETS = [
    {
      id: "relax",
      label: "リラックス",
      hint: "副交感系の昂進・ストレス減",
      apply: { vns: 1.5, hrv_sync: 70, naturesound: 60, aroma: 60, amber620: 70 },
    },
    {
      id: "focus",
      label: "集中",
      hint: "注意・覚醒度を引き上げる",
      apply: { tdcs: 1.2, binaural: 70, pulse_light: 12, circadian: 65 },
    },
    {
      id: "alert",
      label: "覚醒",
      hint: "疲労を抑え覚醒を保つ",
      apply: { tens: 1.0, pulse_light: 18, whitenoise: 30, circadian: 75 },
    },
    {
      id: "recover",
      label: "回復",
      hint: "心拍同期＋アロマで回復方向に",
      apply: { hrv_sync: 80, haptic_chest: 80, aroma: 70, naturesound: 70 },
    },
  ];

  function applyPreset(state, presetId) {
    const preset = PRESETS.find((p) => p.id === presetId);
    if (!preset) return state;
    const next = {};
    INTERVENTIONS.forEach((item) => {
      const cur = state[item.id] || { enabled: false, value: item.defaultValue, response: [] };
      if (preset.apply[item.id] != null) {
        next[item.id] = { ...cur, enabled: true, value: preset.apply[item.id] };
      } else {
        next[item.id] = { ...cur, enabled: false };
      }
    });
    return next;
  }

  function stopAll(state) {
    const next = {};
    INTERVENTIONS.forEach((item) => {
      const cur = state[item.id] || { enabled: false, value: item.defaultValue, response: [] };
      next[item.id] = { ...cur, enabled: false };
    });
    return next;
  }

  function buildDefaultState() {
    const out = {};
    INTERVENTIONS.forEach((item) => {
      out[item.id] = { enabled: false, value: item.defaultValue, response: [] };
    });
    return out;
  }

  function stepResponses(state, constructs) {
    const next = { ...state };
    const now = Date.now();
    INTERVENTIONS.forEach((item) => {
      const s = next[item.id];
      if (!s) return;
      const intensity = (s.value - item.min) / Math.max(1e-6, item.max - item.min);
      const effect = Object.entries(item.impacts).reduce((acc, [, v]) => acc + Math.abs(v), 0);
      const responseScore = s.enabled ? Math.max(0, Math.min(1, 0.3 + 0.55 * intensity + 0.15 * effect)) : 0.05;
      const point = { t: now, v: responseScore };
      const hist = [...s.response, point].slice(-60);
      next[item.id] = { ...s, response: hist };
    });
    return next;
  }

  function computeConstructNudge(state) {
    const nudge = {};
    INTERVENTIONS.forEach((item) => {
      const s = state[item.id];
      if (!s || !s.enabled) return;
      const intensity = (s.value - item.min) / Math.max(1e-6, item.max - item.min);
      Object.entries(item.impacts).forEach(([k, v]) => {
        nudge[k] = (nudge[k] || 0) + v * intensity;
      });
    });
    return nudge;
  }

  window.InterventionEngine = {
    INTERVENTIONS,
    CATEGORY_LABELS,
    CATEGORY_ACCENTS,
    PRESETS,
    buildDefaultState,
    stepResponses,
    computeConstructNudge,
    applyPreset,
    stopAll,
  };
})();

(() => {
  const DEVICES = [
    {
      id: "muse",
      name: "Muse S Athena",
      vendor: "InteraXon",
      modality_routes: [
        { modality: "eeg", source: "head" },
        { modality: "ppg", source: "earL" },
        { modality: "acc", source: "head" },
      ],
    },
    {
      id: "polar",
      name: "Polar H10",
      vendor: "Polar",
      modality_routes: [
        { modality: "ecg", source: "chest" },
        { modality: "acc", source: "chest" },
      ],
    },
    {
      id: "empatica",
      name: "Empatica E4",
      vendor: "Empatica",
      modality_routes: [
        { modality: "ppg", source: "wristL" },
        { modality: "eda", source: "wristL" },
        { modality: "temp", source: "wristL" },
        { modality: "acc", source: "wristL" },
      ],
    },
    {
      id: "oura",
      name: "Oura Ring 4",
      vendor: "Oura",
      modality_routes: [
        { modality: "ppg", source: "finger" },
        { modality: "temp", source: "finger" },
        { modality: "acc", source: "finger" },
      ],
    },
    {
      id: "apple_watch",
      name: "Apple Watch",
      vendor: "Apple",
      modality_routes: [
        { modality: "ppg", source: "wristL" },
        { modality: "ecg", source: "wristL" },
        { modality: "acc", source: "wristL" },
      ],
    },
    {
      id: "openbci",
      name: "OpenBCI Cyton",
      vendor: "OpenBCI",
      modality_routes: [
        { modality: "eeg", source: "head" },
      ],
    },
    {
      id: "xhro",
      name: "XHRO PoC",
      vendor: "XHRO",
      modality_routes: [
        { modality: "eeg", source: "head" },
        { modality: "ecg", source: "chest" },
        { modality: "emg", source: "armR" },
        { modality: "resp", source: "abdomen" },
      ],
    },
    {
      id: "fingertip_pox",
      name: "Fingertip SpO2",
      vendor: "Nonin",
      modality_routes: [
        { modality: "ppg", source: "finger" },
      ],
    },
  ];

  function getDevice(id) {
    return DEVICES.find((d) => d.id === id);
  }

  function getActiveSourcesByModality(connectedDeviceIds) {
    const out = {};
    for (const id of connectedDeviceIds) {
      const dev = getDevice(id);
      if (!dev) continue;
      for (const route of dev.modality_routes) {
        if (!out[route.modality]) out[route.modality] = [];
        if (!out[route.modality].includes(route.source)) {
          out[route.modality].push(route.source);
        }
      }
    }
    return out;
  }

  function getConnectedModalityIds(connectedDeviceIds, fallbackIds = []) {
    const active = getActiveSourcesByModality(connectedDeviceIds);
    const set = new Set(Object.keys(active));
    fallbackIds.forEach((id) => set.add(id));
    return set;
  }

  window.DeviceRegistry = {
    DEVICES,
    getActiveSourcesByModality,
    getConnectedModalityIds,
  };
})();

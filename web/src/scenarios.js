export const SCENARIOS = {
  'Convoy B / Narmada corridor': {
    text:
      'Convoy B must reach Kolar field hospital with medical stores before tomorrow ' +
      'morning. Decide what happens to Convoy B right now, and say what you need from whom.',
    folder: 'scenario_1_convoy',
    files: [
      'dispatch_log_7kilara.txt',
      'bulletin_narmada_rainfall.pdf',
      'IMG_4471_bridge.jpg',
    ],
  },
  'Warehouse cold-chain incident': {
    text:
      'A district warehouse has reported water ingress damaging 40 crates of vaccine ' +
      'stock. Decide the response and name what must happen in the next 6 hours.',
    folder: 'scenario_2_warehouse',
    files: ['warehouse_report.txt', 'coldchain_sop.pdf', 'IMG_4488_block_c.jpg'],
  },
}

export const SCENARIO_NAMES = Object.keys(SCENARIOS)
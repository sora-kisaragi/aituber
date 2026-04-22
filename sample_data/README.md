# Sample Data

This directory contains sample data for development and testing.

## Structure

- `videos/` - Sample MP4 game footage (CC0 or self-recorded, 30s–5min)
- `events/` - Manually annotated event JSON files (e.g. `sample_match_events.json`)
- `annotations/` - Segment-event mapping tables (CSV/TSV)

## Usage

Place a short gameplay clip as `videos/sample_match.mp4` to run the pipeline end-to-end.

Event annotation format:

```json
[
  {
    "timestamp": 12.4,
    "type": "kill",
    "details": { "attacker": "player", "target": "enemy_a" }
  }
]
```

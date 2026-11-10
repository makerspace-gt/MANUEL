# Hermes auf MANUEL

> **Ein Irrweg, festgehalten zum Nachvollziehen.** Am 09.11.2026 haben wir ausprobiert, einen Agenten die Erfassung weitgehend allein machen zu lassen. Das war nicht sinnvoll. Die Ergebnisse brauchten trotzdem eine Durchsicht, und der Weg ließ sich schlechter nachvollziehen als die Läufe mit festen Skripten und ADRs. Die Erkenntnis steht im Fazit der [Fallstudie](../case-study/kapitel/13-fazit.adoc). Die echten Nachrichten und Ergebnisse liegen nicht im Repo, Ticketnummern in den Beispielen sind erfunden.

[Hermes Agent](https://github.com/NousResearch/hermes-agent) von Nous Research läuft auf dem Mini-PC im Container und nutzt `qwen3.6:35b-a3b` aus Ollama. Hier liegt der Skill, mit dem Hermes aus der ersten Nachricht eines Gastes die Gerätedaten für [Restarters.net](https://restarters.net) vorbereitet. Gesendet wird nichts.

## Einrichtung

Hermes läuft rootless als Benutzer `core`, alle Daten liegen in `~/.hermes`. Der Container erreicht Ollama über `--network host` an `127.0.0.1:11434`.

Hermes braucht mindestens 64.000 Tokens Kontext. Ollama läuft für Zammad mit 32.768, und das `num_ctx`, das Hermes über `/v1` mitschickt, ignoriert Ollama. Deshalb gibt es in Ollama den Namen `qwen3.6:35b-a3b-64k` mit denselben Gewichten.

```bash
printf 'FROM qwen3.6:35b-a3b\nPARAMETER num_ctx 65536\n' > /tmp/Modelfile.hermes
sudo podman cp /tmp/Modelfile.hermes ollama:/tmp/Modelfile.hermes
sudo podman exec ollama ollama create qwen3.6:35b-a3b-64k -f /tmp/Modelfile.hermes
```

Ein voller Kontext von 64.000 Tokens braucht etwa 4 bis 5 Minuten bis zum ersten Token, gemessen am 09.11.2026 mit 261 Token/s bei 45.000 Tokens. Die Zeitlimits in `~/.hermes/config.yaml` sind deshalb großzügig gesetzt.

```yaml
model:
  provider: custom
  default: qwen3.6:35b-a3b-64k
  base_url: http://127.0.0.1:11434/v1
  api_key: ollama
  context_length: 65536
  ollama_num_ctx: 65536
agent:
  local_stream_stale_timeout: 1200
compression:
  context_timeout_seconds: 1200
  context_total_ceiling_seconds: 1800
auxiliary:
  compression: {timeout: 1200}
  web_extract: {timeout: 900}
  session_search: {timeout: 900, max_concurrency: 1}
  vision: {timeout: 900}
  title_generation: {timeout: 300}
```

Dazu kommen in `~/.hermes/.env` die Werte `HERMES_API_TIMEOUT=1800` und `HERMES_STREAM_READ_TIMEOUT=1800`. Dateien in `~/.hermes` gehören dem Benutzer des Containers und lassen sich nur mit `podman unshare` ändern.

## Erfassung für Restarters.net

Der Skill [repaircafe-restarters](repaircafe-restarters/SKILL.md) liegt auf dem Gerät unter `~/.hermes/skills/repaircafe/`. Er ordnet jede Nachricht für sich direkt in die Kategorien von Restarters.net ein. Titel des Teams, frühere Einordnungen und der Katalog fließen nicht ein.

[erfassen.py](erfassen.py) gibt jede Nachricht einzeln an Hermes, prüft die Antwort und sammelt alles in einer JSON-Datei. Kategorie und Strom prüft das Skript gegen die Liste von Restarters. Ist das Modell unsicher oder fehlt etwas, steht das Ticket auf `rueckfrage`.

```bash
cd ~/repaircafe
python3 erfassen.py tickets-nachrichten.json restarters.json --limit 20
python3 erfassen.py tickets-nachrichten.json restarters.json            # alle offenen
python3 erfassen.py tickets-nachrichten.json restarters.json --klaeren  # Rückfragen beantworten
```

Ein Lauf lässt sich abbrechen und fortsetzen. Fertige Tickets überspringt das Skript, mit `--neu` bearbeitet es sie erneut. Beim Klären zeigt es Nachricht, Vorschlag und Fragen. Die Antwort geht in dieselbe Sitzung von Hermes zurück.

Je Ticket enthält das Ergebnis den Status, je Gerät die Felder der API von Restarters.net und die Rückfragen. `repair_status`, `spare_parts`, `barrier` und `eventid` bleiben leer, sie folgen erst nach dem Termin.

Nachrichten und Ergebnis enthalten persönliche Daten und gehören nicht in dieses Repo. `problem` ist zusammengefasst und ohne Namen, muss aber vor dem Senden geprüft werden, siehe [ADR 36](../docs/adr/0036-reparaturen-ab-2024-an-restarters-nachmelden.adoc).

## Probe vom 09.11.2026

19 Nachrichten, jeweils einmal ohne und einmal mit Nachdenken.

| Einstellung | Zeit je Nachricht | Beobachtung |
|---|---|---|
| `--reasoning none` | 10 bis 16 s | Kategorien meist richtig, `item_type` öfter zu grob oder falsch, sicher auch bei Fehlern |
| `--reasoning low` | 40 bis 120 s | genauere `item_type` wie `Electric pole saw` oder `Soda maker` |

Standard ist `low`. Alle 752 Nachrichten brauchen damit etwa 15 bis 20 Stunden, mit `none` etwa 3 Stunden. In beiden Fällen hielt das Modell den Zauberstab nicht für einen Stabmixer. Die Ergebnisse brauchen deshalb eine Durchsicht durch das Team.

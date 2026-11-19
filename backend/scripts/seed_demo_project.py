"""Create a small demo project through the public API.

Useful for trying NovelForge offline (USE_MOCK_LLM=true) and for README
screenshots. Everything is sample content; nothing calls a real AI provider
except whatever the running backend is configured to use.

Usage (backend and MongoDB running):

    python backend/scripts/seed_demo_project.py
    python backend/scripts/seed_demo_project.py --api http://localhost:8000
"""
from __future__ import annotations

import argparse
import sys

import httpx

PROJECT = {
    "title": "The Lighthouse Archive",
    "idea_dump": (
        "On a storm-bound island, a young archivist discovers that the old "
        "lighthouse keeps a logbook of every ship it failed to save - and the "
        "newest entry is dated tomorrow."
    ),
    "genre": "Mystery",
    "tone": "Atmospheric, quietly tense",
}

VISION = {
    "premise": PROJECT["idea_dump"],
    "genre": "Literary mystery",
    "themes": ["Memory and responsibility", "The cost of keeping secrets"],
    "target_length": "Novel (about 80,000 words)",
    "inspirations": ["Coastal folklore", "Archive mysteries"],
    "audience": "Adult readers of character-driven mysteries",
    "narrative_goals": [
        "Reveal who keeps writing the logbook",
        "Force Ada to choose between the island's comfort and the truth",
    ],
}

ENTRIES = [
    ("character", "Ada Venn", "A 24-year-old archivist sent to catalogue the island's records. Careful, curious, and bad at leaving questions alone."),
    ("character", "Tomas Hale", "The retired lighthouse keeper. Kind to Ada, evasive about the night the Meridian sank thirty years ago."),
    ("character", "Ines Marr", "Harbour master and Tomas's oldest friend. Wants the island's past to stay buried."),
    ("world", "Grey Holm island", "A small fishing island cut off by winter storms for weeks at a time. The lighthouse has been automated for a decade, yet its lamp room is still locked every night."),
    ("theme", "Memory and responsibility", "Who is responsible for remembering the people a community failed?"),
    ("plot_thread", "The future-dated entry", "The logbook's newest entry names a ship that has not sailed yet. Ada must find out who wrote it before the date arrives."),
    ("mystery", "Who writes the logbook?", "The handwriting matches Tomas's, but he says he has not climbed the tower in years."),
    ("timeline", "The Meridian sinks", "Thirty years before the story, the fishing boat Meridian is lost in a storm while the lamp is dark."),
]

CHAPTERS = [
    (
        "Ada arrives on the island and finds the logbook.",
        """The ferry left Ada Venn on the pier with two suitcases and a letter of introduction that nobody asked to see. Grey Holm smelled of salt and diesel, and the wind came in sideways, as if it had been waiting for her.

Tomas Hale met her at the archive door. He was older than his voice on the phone, with careful hands and a habit of looking past her toward the sea. "Most of it is tide tables," he said. "And weddings. People here marry in winter, when there is nothing else to do."

The records were worse than he promised. Boxes swollen with damp, ledgers glued together, a century of births written in four different inks. Ada worked until the windows turned black, then followed the only light left on the island: the lighthouse, sweeping the harbour every nine seconds.

The lamp room was locked. The keeper's office below it was not. On the desk lay a logbook bound in oilcloth, its spine cracked from use. Each page listed a ship, a date, and a single line: lamp dark, no rescue.

The first entry was from 1891. The handwriting changed every few decades, as keepers came and went. Ada turned the pages faster, the way she did when a record started to tell a story it had not meant to tell.

The last entry was neat and recent. The ink had not yet faded.

Silver Wren. 14 November. Lamp dark, no rescue.

Ada checked her phone twice. Today was the thirteenth.""",
    ),
    (
        "Ada asks Tomas about the handwriting; Ines warns her off.",
        """Tomas took the logbook from her the way someone takes a photograph of a person they have lost. He did not open it.

"That is my handwriting," Ada said. "I compared it with the harbour ledgers. The loops on the g, the way you cross the sevens."

"I have not been up that tower in eleven years." He set the book down on the kitchen table, between the bread and the salt. "When they automated the lamp, they took my key."

"Then who has one?"

He did not answer, and the kettle filled the silence for him.

On her way back through the village, Ada found Ines Marr waiting at the harbour office, arms folded against the cold. The harbour master had a voice that carried over engines.

"The Silver Wren is my brother's boat," Ines said. "She goes out at dawn tomorrow, weather permitting. Weather will permit."

"Then you have seen the entry."

"I have seen a lot of entries." Ines looked toward the tower, where the lamp turned and turned. "Thirty years ago the light went dark for one night, and the Meridian went down with six men on board. The island decided it was nobody's fault. You should let it stay nobody's fault, Miss Venn. It is kinder to the living."

Ada walked home along the sea wall. Behind her, the beam swept the water every nine seconds, steady as a heartbeat.

At three in the morning, it stopped.""",
    ),
]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--api", default="http://localhost:8000", help="Backend base URL")
    args = parser.parse_args()

    with httpx.Client(base_url=args.api, timeout=300) as client:
        project = client.post("/api/projects", json=PROJECT).raise_for_status().json()
        pid = project["id"]
        print(f"Created project {project['title']!r} ({pid})")

        client.put(f"/api/projects/{pid}", json={"story_title": PROJECT["title"]}).raise_for_status()
        client.put(f"/api/projects/{pid}/story-vision", json=VISION).raise_for_status()
        for area, title, details in ENTRIES:
            client.post(
                f"/api/projects/{pid}/workspace-entries",
                json={"area": area, "title": title, "details": details, "source_mode": "manual"},
            ).raise_for_status()
        print(f"Added story vision and {len(ENTRIES)} story-bible entries")

        for number, (instruction, prose) in enumerate(CHAPTERS, start=1):
            words = len(prose.split())
            generated = client.post(
                f"/api/projects/{pid}/discovery-writing",
                json={
                    "instruction": instruction,
                    "chapter_number": number,
                    "target_word_min": max(1, words - 100),
                    "target_word_count": words,
                    "target_word_max": words + 200,
                },
            ).raise_for_status().json()
            draft_id = generated["draft"]["draft_id"]
            # Replace the generated text with the author's sample prose, exactly
            # as an author would after editing a draft in the Writing view.
            edited = client.put(
                f"/api/projects/{pid}/chapter-drafts/{draft_id}/content",
                json={"edited_text": prose, "reason": "Demo chapter text"},
            ).raise_for_status().json()
            final_id = edited["draft"]["draft_id"]
            approval = client.put(
                f"/api/projects/{pid}/chapter-drafts/{final_id}/status",
                json={"status": "approved", "reason": "Demo chapter approved"},
            )
            state = "approved" if approval.is_success else f"left as draft ({approval.status_code})"
            print(f"Chapter {number}: {words} words, {state}")

    print(f"Open http://localhost:3000/project/{pid}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

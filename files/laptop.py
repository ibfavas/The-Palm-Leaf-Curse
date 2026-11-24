from pathlib import Path
import subprocess
import tempfile
from zipfile import ZIP_DEFLATED, ZipFile

from .leaves import scan


def laptop(destination, note, transcription, entry):
    with tempfile.TemporaryDirectory() as stage:
        work = Path(stage)
        scan(34, 1).save(work / "34r.png")
        with ZipFile(work / "folio-34.zip", "w", compression=ZIP_DEFLATED) as folder:
            folder.write(work / "34r.png", "34r.png")
            folder.writestr("transcription.txt", transcription + "\n")
            folder.writestr("personal.txt", note + "\n\n" + entry + "\n")
        records = {
            "accessions.tsv": "Accession\tCount\tMaterial\nMS-1794-047\t34\tPalm leaf\nMP-1931-012\t1\tSurvey map\n",
            "expenses.txt": "Manuscript desk\nLamp repair — 140\nBinding cord — 35\nCotton gloves — 90\n",
            "appointments.txt": "Wednesday, 4 pm — humidity reading\nFriday, 11 am — return ledger to reading room\n",
        }
        commands = ["mkdir papers"]
        for filename, text in records.items():
            (work / filename).write_text(text)
            commands.append(f"write {filename} papers/{filename}")
        commands += ["write folio-34.zip papers/folio-34.zip", "rm papers/folio-34.zip"]
        with destination.open("wb") as disk:
            disk.truncate(12 * 1024 * 1024)
        subprocess.run(["mke2fs", "-q", "-t", "ext2", "-F", "-b", "1024", "-g", "1024",
                        "-L", "RM_WORK", str(destination)], check=True, capture_output=True)
        result = subprocess.run(["debugfs", "-w", "-f", "-", str(destination)], input="\n".join(commands)+"\n",
                                cwd=work, text=True, capture_output=True, check=True)
        # debugfs can report a failed batch command while exiting successfully.
        if result.stdout.count("Allocated inode:") != len(records) + 1 or len(result.stderr.splitlines()) > 1:
            raise RuntimeError("The working disk could not be assembled.")

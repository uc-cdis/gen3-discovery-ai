## Extracting and cleaning data from AggMDS

You will need a current credentials file ```credentials.json``` from the common you what the data for. Make sure
its in ```~/.gen3/credentials.json```

create a directory ```data``` and ```cd data```
In that directory run:
```
python../mds/extract.py
```
the will create a file ```brh-data-commons-org-discovery_metadata.tsv```

Some descriptions are too long and we don't need to use the __manifest files so the
file cleanBRGdata.py will help cleanup the data so that it can be used.

run:
```
python ../mds/cleanBRHData.py --src data/brh-data-commons-org-discovery_metadata.tsv --dst data/default_cleaned.tsv
```

you show be able to use ```data/default_cleaned.tsv``` as the input to
the loading data steps described in the README for the AiService.

from gen3.tools.metadata.discovery import (
    output_expanded_discovery_metadata,
)
from gen3.utils import get_or_create_event_loop_for_thread
from gen3.auth import Gen3Auth

if __name__ == "__main__":
    auth = Gen3Auth()
    loop = get_or_create_event_loop_for_thread()
    loop.run_until_complete(
        output_expanded_discovery_metadata(
            auth, endpoint="brh.datacommons.org", output_format="tsv", use_agg_mds=True
        )
    )

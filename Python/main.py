# main.py

import garmin_export
import json_ingest
import feed_the_duck

def main():
    garmin_export.main()
    json_ingest.main()
    feed_the_duck.main()

if __name__ == "__main__":
    main()
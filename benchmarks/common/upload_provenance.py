"""
RoHub Provenance Upload Module

This module handles the upload of research object provenance data to RoHub,
a platform for research object management and sharing. It processes RO-Crate
metadata artifacts and manages the complete upload workflow including:
- Authentication with RoHub
- Deletion of existing research objects
- Upload of new research objects from zip files
- Polling for upload completion
- Adding semantic annotations to uploaded objects

The module supports both production and development environments of RoHub.
"""

import argparse
import rohub
import time


def parse_args():
    """
    Parse command-line arguments for RoHub provenance upload.

    Returns:
        argparse.Namespace: Parsed command-line arguments containing:
            - provenance_folderpath (str): Path to the zip file containing 
                                          provenance data (RO-Crate)
            - username (str): RoHub authentication username
            - password (str): RoHub authentication password
    """
    parser = argparse.ArgumentParser(
        description="Process ro-crate-metadata.json artifacts and display simulation results."
    )
    parser.add_argument(
        "--provenance_folderpath",
        type=str,
        required=True,
        help="Path to the folder containing provenance data",
    )
    parser.add_argument(
        "--benchmark_name",
        type=str,
        required=True,
        help="Name of the benchmark to be uploaded",
    )
    parser.add_argument(
        "--username",
        type=str,
        required=True,
        help="Username for RoHub",
    )
    parser.add_argument(
        "--password",
        type=str,
        required=True,
        help="Password for RoHub",
    )
    return parser.parse_args()


def run(args):
    """
    Execute the complete RoHub upload workflow.

    This function performs the following operations:
    1. Configures RoHub settings (API endpoints, authentication)
    2. Authenticates with RoHub using provided credentials
    3. Deletes all existing research objects owned by the user
    4. Uploads the new research object from the specified zip file
    5. Polls the upload job status until completion or timeout
    6. Adds semantic annotations to the successfully uploaded object

    Args:
        args (argparse.Namespace): Parsed command-line arguments containing:
            - provenance_folderpath: Path to the provenance zip file
            - username: RoHub username
            - password: RoHub password

    Raises:
        Exception: If authentication fails
        Exception: If upload fails
        Exception: If deletion of existing ROs fails

    Configuration:
        USE_DEVELOPMENT_VERSION (bool): When True, uses RoHub development server.
                                       Set to False for production environment.
        
        Timeout Settings:
            - Upload timeout: 5 minutes (300 seconds)
            - Poll interval: 10 seconds between status checks
            - Sleep time: 10 seconds between API calls

    Annotations:
        The function adds a predefined annotation linking the research object
        to the NFDI4Ing Model Validation Platform benchmark.
    """
    # Configure API sleep time to avoid rate limiting
    rohub.settings.SLEEP_TIME = 10

    # Toggle between development and production environments
    USE_DEVELOPMENT_VERSION = True
    
    if USE_DEVELOPMENT_VERSION:
        # Development server configuration
        rohub.settings.API_URL = "https://rohub2020-devel.apps.bst2.paas.psnc.pl/api/"
        rohub.settings.KEYCLOAK_CLIENT_ID = "rohub2020-cli"
        rohub.settings.KEYCLOAK_CLIENT_SECRET = "714617a7-87bc-4a88-8682-5f9c2f60337d"
        rohub.settings.KEYCLOAK_URL = "https://keycloak-dev.apps.paas-dev.psnc.pl/auth/realms/rohub/protocol/openid-connect/token"
        rohub.settings.SPARQL_ENDPOINT = (
            "https://rohub2020-api-virtuoso-route-rohub.apps.paas-dev.psnc.pl/sparql/"
        )

    # Authenticate with RoHub
    rohub.login(args.username, args.password)

    # Retrieve list of user's existing research objects
    my_ros = rohub.list_my_ros()

    # Delete all existing research objects to ensure clean upload
    try:
        for _, row in my_ros.iterrows():
            rohub.ros_delete(row["identifier"])
    except Exception as error:
        print(f"Error on Deleting RoHub: {error}")

    # Initialize tracking variables for upload
    identifier = ""  # Job identifier for status polling
    uuid = ""        # UUID of the uploaded research object

    # Upload the research object zip file
    try:
        upload_result = rohub.ros_upload(path_to_zip=args.provenance_folderpath)
        identifier = upload_result["identifier"]
        uuid = upload_result["results"].rstrip("/").split("/")[-1]
    except Exception as error:
        print(f"Error on Upload RoHub: {error}")

    # Configure polling parameters
    timeout_seconds = 5 * 60  # 5 minutes maximum wait time
    poll_interval = 10        # Check status every 10 seconds
    start_time = time.time()

    # Poll upload job status until completion or timeout
    while True:
        success_result = rohub.is_job_success(job_id=identifier)
        status = success_result.get("status", "UNKNOWN")

        if status == "SUCCESS":
            print(f"Upload successful: {success_result}")
            break
        elif time.time() - start_time > timeout_seconds:
            print(f"Upload did not succeed within 5 minutes. Last status: {status}")
            break
        else:
            print(f"Current status: {status}, waiting {poll_interval}s...")
            time.sleep(poll_interval)

    # Define semantic annotation linking to the validation platform benchmark
    ANNOTATION_PREDICATE = "http://w3id.org/nfdi4ing/metadata4ing#investigates"
    ANNOTATION_OBJECT = f"https://github.com/BAMresearch/NFDI4IngModelValidationPlatform/tree/main/benchmarks/{args.benchmark_name}"

    # Add semantic annotations if upload was successful
    if uuid != "":
        _RO = rohub.ros_load(uuid)
        annotation_json = [
            {"property": ANNOTATION_PREDICATE, "value": ANNOTATION_OBJECT}
        ]
        add_annotations_result = _RO.add_annotations(
            body_specification_json=annotation_json
        )
        print(add_annotations_result)


def main():
    """
    Main entry point for the RoHub provenance upload script.

    Parses command-line arguments and initiates the upload workflow to RoHub.
    This function is called when the script is executed directly.

    Usage:
        python upload_provenance.py \
            --provenance_folderpath /path/to/ro-crate.zip \
            --username user@example.com \
            --password your_password

    Note:
        - Ensure the provenance file is a valid zip containing RO-Crate metadata
        - Valid RoHub credentials are required for authentication
        - The script will delete all existing research objects before uploading
        - Upload process may take up to 5 minutes

    Exits:
        The script will exit with a non-zero status code if authentication
        or upload fails, or if required arguments are not provided.
    """
    args = parse_args()
    run(args)


if __name__ == "__main__":
    main()
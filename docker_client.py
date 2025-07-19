import os
import docker
import docker.errors
from dotenv import dotenv_values
from docker.errors import NotFound, APIError, BuildError, ContainerError

client = docker.from_env()


def initialize_project(project_path: str, project_name: str):
    """
    Build Docker image for the project.
    """
    try:
        image, _ = client.images.build(path=project_path, tag=project_name)
        return image
    except BuildError as e:
        print(f"Build failed: {e}")
    except APIError as e:
        print(f"Docker API error: {e}")


def run_project(project_name: str, env_file: str = None, ports: dict = None):
    """
    Start a Docker container from an image.
    """
    try:
        # Remove old container if it exists
        try:
            old = client.containers.get(project_name)
            old.stop()
            old.remove()
            print(f"Old container '{project_name}' removed.")
        except NotFound:
            pass

        env_vars: dict = dotenv_values(env_file)

        container = client.containers.run(
            image=project_name,
            name=project_name,
            environment=env_vars,
            ports=ports,
            detach=True,
        )
        print(f"Container '{project_name}' started.")
        return container
    except ContainerError as e:
        print(f"Container error: {e}")
    except APIError as e:
        print(f"Docker API error: {e}")


def stop_project(project_name: str):
    """
    Stop a running Docker container.
    """
    try:
        container = client.containers.get(project_name)
        container.stop()
        print(f"Container '{project_name}' stopped.")
    except NotFound:
        print(f"Container '{project_name}' not found.")
    except APIError as e:
        print(f"Stop error: {e}")


def restart_project(
    project_name: str, has_changes: bool = False, project_path: str = None
):
    """
    Restart the Docker container.
    If `has_changes` is True, rebuild the image before restarting.
    """
    try:
        if has_changes:
            if not project_path:
                print("Project path must be provided to rebuild the image.")
                return
            print(f"Rebuilding image for '{project_name}' due to changes...")
            try:
                client.images.remove(image=project_name, force=True)
                print(f"Old image '{project_name}' removed.")
            except docker.errors.ImageNotFound:
                print(f"No existing image '{project_name}' to remove.")
            initialize_project(project_path, project_name)

        restart_container(project_name)

    except APIError as e:
        print(f"Restart error: {e}")


def restart_container(project_name: str):
    try:
        container = client.containers.get(project_name)
        container.restart()
        print(f"Container '{project_name}' restarted.")
    except NotFound:
        print(f"Container '{project_name}' not found.")
    except APIError as e:
        print(f"Restart error: {e}")


def get_logs(project_name: str, tail: int = 100):
    """
    Get the latest logs from the container.
    """
    try:
        container = client.containers.get(project_name)
        logs = container.logs(tail=tail).decode()
        print(f"--- Logs from '{project_name}' ---\n{logs}")
        return logs
    except NotFound:
        print(f"Container '{project_name}' not found.")
    except APIError as e:
        print(f"Logs error: {e}")


def stream_logs(project_name: str):
    """
    Stream logs in real time from a running Docker container.
    """
    try:
        container = client.containers.get(project_name)
        print(f"--- Streaming logs from '{project_name}' (Press Ctrl+C to stop) ---")
        for log in container.logs(stream=True, follow=True):
            print(log.decode('utf-8'), end='')
    except NotFound:
        print(f"Container '{project_name}' not found.")
    except APIError as e:
        print(f"Logs error: {e}")
    except KeyboardInterrupt:
        print("\nStopped streaming logs.")

# Deploying Paper Trading System on Raspberry Pi

This guide explains how to easily deploy the Paper Trading System on a Raspberry Pi using the provided setup script.

## Prerequisites

-   A Raspberry Pi with Raspberry Pi OS installed.
-   Internet connection.
-   Access to the terminal (SSH or direct).

## Deployment Steps

1.  **Clone the Repository**

    Navigate to your home directory (or desired location) and clone the repository:

    ```bash
    cd ~
    git clone <repository_url>
    cd <repository_folder>/paper-trading
    ```
    *(Replace `<repository_url>` with the actual URL of this repo and `<repository_folder>` with the folder name)*

2.  **Make the Script Executable**

    Give execution permission to the setup script:

    ```bash
    chmod +x setup_pi.sh
    ```

3.  **Run the Setup Script**

    Execute the script. It will install dependencies, create a virtual environment, and set up the systemd service.

    ```bash
    ./setup_pi.sh
    ```

    *Note: The script uses `sudo` for system commands, so you may be prompted for your password.*

4.  **Verify Installation**

    Once the script completes, it will show the status of the service. You can also check it manually:

    ```bash
    sudo systemctl status paper-trading.service
    ```

    The service should be `active (running)`.

## Managing the Service

Here are common commands to manage the trading bot:

-   **Start the bot:**
    ```bash
    sudo systemctl start paper-trading.service
    ```

-   **Stop the bot:**
    ```bash
    sudo systemctl stop paper-trading.service
    ```

-   **Restart the bot:**
    ```bash
    sudo systemctl restart paper-trading.service
    ```

-   **View Logs:**
    To see the live output of the bot:
    ```bash
    sudo journalctl -u paper-trading.service -f
    ```
    *(Press `Ctrl+C` to exit the log view)*

-   **Disable (prevent auto-start on boot):**
    ```bash
    sudo systemctl disable paper-trading.service
    ```

## Accessing the Dashboard

By default, the web dashboard runs on port `5000`. Open a web browser on your computer and navigate to:

```
http://<raspberry_pi_ip_address>:5000
```

*(Replace `<raspberry_pi_ip_address>` with the actual IP address of your Pi, e.g., `192.168.1.100`)*

## Configuration

To change settings (trading pairs, strategy, etc.):

1.  Edit the `config.yaml` file:
    ```bash
    nano config.yaml
    ```
2.  Save changes (`Ctrl+O`, `Enter`) and exit (`Ctrl+X`).
3.  Restart the service to apply changes:
    ```bash
    sudo systemctl restart paper-trading.service
    ```

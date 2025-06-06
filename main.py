import os
import csv
import requests
from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt, IntPrompt
from rich.table import Table
from rich.style import Style
from rich.progress import Progress

console = Console()

load_dotenv()
access_token = os.getenv('access_token')
refresh_token = os.getenv('refresh_token')
url = os.getenv('url')

ACTIONS = {
    1: 'Register new user',
    2: 'Create account',
    3: 'Grant KYC',
    4: 'Assign subscription',
    5: 'Exit'
}

panel_style = Style(color="#abb2bf", bgcolor="#282c34", bold=True)
title_style = Style(color="#61afef", bold=True)
error_style = Style(color="#e06c75", bold=True)
success_style = Style(color="#98c379", bold=True)
warning_style = Style(color="#e5c07b", bold=True)


def get_auth_headers(token):
    return {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json'
    }


def get_available_subscriptions():
    headers = get_auth_headers(access_token)

    try:
        with Progress(transient=True) as progress:
            task = progress.add_task("[cyan]Fetching subscriptions...", total=1)

            response = requests.get(
                f"{url}/reg/subscription/details/available",
                headers=headers
            )

            progress.update(task, advance=1)

        if response.status_code == 200:
            subscriptions_data = response.json()

            subscriptions = {}
            for sub in subscriptions_data:
                subscriptions[sub['name']] = sub['id']

            return subscriptions
        else:
            console.print(f"Error getting subscriptions: {response.status_code}", style=error_style)
            console.print(response.text, style=error_style)
            return None

    except requests.exceptions.RequestException as e:
        console.print(f"Request failed: {str(e)}", style=error_style)
        return None


def register_user():
    console.print(Panel.fit("Register New User", style=title_style))
    email = input('Enter email: ')
    password = input('Enter password: ')

    request_body = {
        "userType": "CUSTOMER",
        "email": email,
        "password": password,
        "emailConfirmCode": "12345",
    }

    headers = {
        "partnerId": "3",
    }

    response = requests.post(
        f"{url}/reg/user",
        json=request_body,
        headers=headers
    )

    if response.status_code == 200:
        response_data = response.json()
        save_credentials(response_data, email, password)
        print("User registered successfully!")
    else:
        print(f"Error: {response.status_code} - {response.text}")



def save_credentials(response_data, email, password):
    creds = [
        response_data.get('access_token'),
        response_data.get('refresh_token'),
        password,
        email
    ]

    with open('user_creds.csv', 'w', newline='') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(['Access Token', 'Refresh Token', 'Password', 'Email'])
        writer.writerow(creds)


def create_account():
    console.print(Panel.fit("Create Account", style=title_style))

    table = Table(show_header=False, box=None)
    table.add_row("1. My account (using configured access token)")
    table.add_row("2. Another user (provide access token)")
    console.print(table)

    choice = Prompt.ask("Select option", choices=["1", "2"], default="1", console=console)

    if choice == '1':
        token = access_token
        console.print("Using configured access token...", style=warning_style)
    elif choice == '2':
        token = Prompt.ask("Enter user's access token", console=console)
    else:
        console.print("Invalid choice, returning to main menu", style=error_style)
        return

    account_type = Prompt.ask(
        "Enter account type",
        choices=["CHECKING", "SAVINGS", "BUSINESS"],
        default="CHECKING",
        console=console
    )

    headers = get_auth_headers(token)
    headers['accountType'] = account_type

    try:
        with Progress(transient=True) as progress:
            task = progress.add_task("[cyan]Creating account...", total=1)

            response = requests.post(
                f"{url}/wallet/account?accountType={account_type}",
                headers=headers
            )

            progress.update(task, advance=1)

        console.print(f"\nStatus: {response.status_code}", style=warning_style)

        try:
            response_data = response.json()
            console.print("Response:", response_data)

            if response.status_code == 200:
                console.print("Account created successfully!", style=success_style)
                if choice == '2':
                    console.print("Note: This account was created with provided access token", style=warning_style)
        except ValueError:
            console.print("Response text:", response.text)

    except requests.exceptions.RequestException as e:
        console.print(f"Request failed: {str(e)}", style=error_style)


def grant_kyc():
    console.print(Panel.fit("Grant KYC Verification", style=title_style))

    headers = get_auth_headers(access_token)
    request_body = {
        "level": Prompt.ask("Enter KYC level", choices=["L1", "L2"], default="L1", console=console),
        "type": "SUMSUB"
    }

    user_id = Prompt.ask("Enter user id", console=console)

    with Progress(transient=True) as progress:
        task = progress.add_task("[cyan]Processing KYC...", total=1)

        response = requests.post(
            f"{url}/reg/admin/verification/user?userId={user_id}",
            json=request_body,
            headers=headers
        )

        progress.update(task, advance=1)

    console.print(f"\nStatus: {response.status_code}", style=warning_style)
    try:
        console.print("Response:", response.json())
        if response.status_code == 200:
            console.print(f"Successfully KYC {request_body['level']} granted!", style=success_style)
    except ValueError:
        console.print("Response text:", response.text)


def assign_subscription():
    console.print(Panel.fit("Assign Subscription", style=title_style))

    subscriptions = get_available_subscriptions()
    if not subscriptions:
        console.print("Failed to get subscriptions list", style=error_style)
        return

    table = Table(title="Available Subscriptions", show_lines=True)
    table.add_column("#", style="cyan")
    table.add_column("Name", style="magenta")
    table.add_column("ID", style="green")

    for i, (name, sub_id) in enumerate(subscriptions.items(), 1):
        table.add_row(str(i), name, str(sub_id))

    console.print(table)

    try:
        choices = [str(i) for i in range(1, len(subscriptions) + 1)]
        choice = Prompt.ask("Select subscription", choices=choices, console=console)
        choice = int(choice)

        if choice < 1 or choice > len(subscriptions):
            console.print("Invalid selection", style=error_style)
            return

        sub_name = list(subscriptions.keys())[choice - 1]
        sub_id = subscriptions[sub_name]

        console.print(f"Assigning [magenta]{sub_name}[/] subscription...", style=warning_style)
        user_id = Prompt.ask("Enter user id", console=console)

        request_body = {
            "subscriptionDetailsId": sub_id,
            "userId": user_id
        }

        headers = get_auth_headers(access_token)

        with Progress(transient=True) as progress:
            task = progress.add_task("[cyan]Assigning subscription...", total=1)

            response = requests.post(
                f"{url}/reg/admin/subscription/entries/subscription_entities",
                json=request_body,
                headers=headers
            )

            progress.update(task, advance=1)

        console.print(f"\nStatus: {response.status_code}", style=warning_style)
        try:
            console.print("Response:", response.json())
            if response.status_code == 200:
                console.print(f"Successfully assigned [magenta]{sub_name}[/] subscription!", style=success_style)
        except ValueError:
            console.print("Response text:", response.text)

    except ValueError:
        console.print("Please enter a valid number", style=error_style)


def main():
    console.print(Panel.fit("Admin Dashboard", style=title_style, subtitle="v1.0"))

    while True:
        table = Table(title="Available Actions", show_header=True, header_style="bold cyan")
        table.add_column("Option", style="cyan")
        table.add_column("Action", style="white")

        for num, action in ACTIONS.items():
            table.add_row(str(num), action)

        console.print(table)

        try:
            choice = IntPrompt.ask(
                "Select action",
                choices=[str(i) for i in ACTIONS.keys()],
                show_choices=False,
                console=console
            )

            if choice not in ACTIONS:
                console.print("Invalid choice, try again", style=error_style)
                continue

            if choice == 1:
                register_user()
            elif choice == 2:
                create_account()
            elif choice == 3:
                grant_kyc()
            elif choice == 4:
                assign_subscription()
            elif choice == 5:
                console.print("Exiting...", style=warning_style)
                break

        except ValueError:
            console.print("Please enter a number", style=error_style)
        except Exception as e:
            console.print(f"An error occurred: {str(e)}", style=error_style)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        console.print("\nOperation cancelled by user", style=error_style)
    except Exception as e:
        console.print(f"Fatal error: {str(e)}", style=error_style)
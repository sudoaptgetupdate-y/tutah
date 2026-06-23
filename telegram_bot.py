import requests
import os

def send_telegram_report(bot_token, chat_id, image_path, caption):
    if not bot_token or not chat_id:
        return False, "Error: Telegram configuration missing."
    
    url = f"https://api.telegram.org/bot{bot_token}/sendPhoto"
    
    try:
        with open(image_path, 'rb') as photo:
            files = {'photo': photo}
            data = {'chat_id': chat_id, 'caption': caption}
            response = requests.post(url, files=files, data=data)
            
        if response.status_code == 200:
            return True, "Report sent successfully."
        else:
            return False, f"Failed to send report: {response.text}"
    except Exception as e:
        return False, f"Error sending to Telegram: {e}"

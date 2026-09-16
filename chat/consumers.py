import json
import uuid
from channels.generic.websocket import AsyncWebsocketConsumer

# Global queue for matchmaking
waiting_users = []

class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.room_group_name = None
        await self.accept()
        await self.search_for_partner()

    async def search_for_partner(self):
        global waiting_users
        if waiting_users:
            # Match found! Pop the first waiting user's channel_name
            partner_channel_name = waiting_users.pop(0)
            self.room_group_name = f"chat_{uuid.uuid4().hex}"
            
            # I join the new room
            await self.channel_layer.group_add(
                self.room_group_name, self.channel_name
            )
            
            # Tell the partner to join my room
            await self.channel_layer.send(
                partner_channel_name,
                {
                    "type": "join_room",
                    "room_group_name": self.room_group_name
                }
            )
            
            welcome_msg = {
                "type": "system_message",
                "message": "You are now chatting with a stranger. Say Hi! 👋",
                "action": "connected"
            }
            
            # Send welcome message to myself directly
            await self.channel_layer.send(self.channel_name, welcome_msg)
            # Send welcome message to partner directly
            await self.channel_layer.send(partner_channel_name, welcome_msg)
            
        else:
            # Nobody is waiting, so I join the queue
            waiting_users.append(self.channel_name)
            await self.send(text_data=json.dumps({
                "type": "system",
                "message": "Waiting for a stranger to connect...",
                "action": "waiting"
            }))

    async def join_room(self, event):
        # Triggered by another user who found me in the queue
        self.room_group_name = event["room_group_name"]
        await self.channel_layer.group_add(
            self.room_group_name, self.channel_name
        )

    async def disconnect(self, close_code):
        global waiting_users
        if self.channel_name in waiting_users:
            waiting_users.remove(self.channel_name)
        
        await self.leave_current_room_and_notify()

    async def receive(self, text_data):
        text_data_json = json.loads(text_data)
        action = text_data_json.get("action")
        
        if action == "disconnect":
            global waiting_users
            if self.channel_name in waiting_users:
                waiting_users.remove(self.channel_name)
            await self.leave_current_room_and_notify()
            await self.send(text_data=json.dumps({
                "type": "system",
                "message": "You disconnected.",
                "action": "disconnected"
            }))
            return
            
        if action == "next":
            # Leave current room, notify partner, and search again
            global waiting_users
            if self.channel_name in waiting_users:
                waiting_users.remove(self.channel_name)
            await self.leave_current_room_and_notify()
            await self.search_for_partner()
            return
            
        message = text_data_json.get("message")
        if message and self.room_group_name:
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    "type": "chat_message",
                    "message": message,
                    "sender_channel": self.channel_name
                }
            )

    async def leave_current_room_and_notify(self):
        if self.room_group_name:
            # Notify the partner that I disconnected
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    "type": "system_message",
                    "message": "Stranger has disconnected.",
                    "action": "disconnected",
                    "exclude_channel": self.channel_name
                }
            )
            # Leave the group
            await self.channel_layer.group_discard(
                self.room_group_name, self.channel_name
            )
            self.room_group_name = None

    async def chat_message(self, event):
        sender_channel = event.get("sender_channel")
        # Identify if message is from self or the stranger
        sender = "You" if sender_channel == self.channel_name else "Stranger"
        
        await self.send(text_data=json.dumps({
            "type": "chat",
            "message": event["message"],
            "sender": sender
        }))
        
    async def system_message(self, event):
        # Don't send the disconnect message to the person who disconnected
        if event.get("exclude_channel") == self.channel_name:
            return
            
        await self.send(text_data=json.dumps({
            "type": "system",
            "message": event["message"],
            "action": event.get("action")
        }))

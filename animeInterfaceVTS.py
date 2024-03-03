import asyncio
from dotenv import load_dotenv, set_key
from os import getenv
from json import dumps, loads
import websockets

class VTSController:
    def __init__(self, port=8001, plugin_name="Misato-therapist", plugin_developer="Karan"):
        self.base_info = {"pluginName": plugin_name, "pluginDeveloper": plugin_developer}
        self.port = port
        self.vts_token = None
        self.websocket = None

    async def initialize(self):
        load_dotenv(override=True)
        self.vts_token = getenv("VTS_TOKEN")
        self.websocket = await websockets.connect(f"ws://localhost:{self.port}")
        res = await self.send_request()
        if not res["data"]["currentSessionAuthenticated"]:
            await self.authenticate()

    async def send_request(self, message_type="APIStateRequest", data=None):
        request = {"apiName": "VTubeStudioPublicAPI", "apiVersion": "1.0",
                   "requestID": "unknown", "messageType": message_type, "data": data or {}}
        await self.websocket.send(dumps(request))
        return loads(await self.websocket.recv())

    async def authenticate(self):
        auth_data = self.base_info
        if self.vts_token:
            auth_data["authenticationToken"] = self.vts_token
        res = await self.send_request("AuthenticationRequest" if self.vts_token else "AuthenticationTokenRequest", auth_data)
        if "APIError" == res["messageType"]:
            raise Exception(f"Error occurred:\n{res['data']['message']}")
        if not res["data"].get("authenticated", True):
            self.vts_token = res["data"]["authenticationToken"]
            set_key(".env", "VTS_TOKEN", self.vts_token)

    async def inject_params(self, params):
        data = {"facefound": False, "mode": "Set",
                "parameterValues": [{"id": param[0], "value": param[1]} for param in params]}
        await self.send_request("InjectParameterDataRequest", data)

async def main():
    vts_controller = VTSController()
    await vts_controller.initialize()
    params = [["MouthOpen", 0.0], ["MouthOpen", 1.0]]
    while True:
        await vts_controller.inject_params(params)
        await asyncio.sleep(1)

asyncio.run(main() if __name__ == "__main__" else None)

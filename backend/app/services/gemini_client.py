import httpx
import json
from typing import AsyncGenerator, Optional

GOOGLE_API_URL = "https://cloudcode-pa.googleapis.com/v1internal"


class GeminiClient:
    """Gemini API 客户端 - 直接调用 Google Cloud API"""
    
    def __init__(self, access_token: str, project_id: str = ""):
        self.access_token = access_token
        self.project_id = project_id
    
    def _get_headers(self):
        return {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }
    
    def _clean_model_name(self, model: str) -> str:
        """清理模型名"""
        # 移除前缀
        for prefix in ["假流式/", "流式抗截断/"]:
            if model.startswith(prefix):
                model = model[len(prefix):]
        return model
    
    async def chat_completions(self, model: str, messages: list, **kwargs) -> dict:
        """非流式聊天补全"""
        model = self._clean_model_name(model)
        
        # 转换 OpenAI 消息格式到 Gemini 格式
        contents = self._convert_messages(messages)
        
        payload = {
            "model": model,
            "project": self.project_id,
            "request": {
                "contents": contents,
                "generationConfig": self._build_generation_config(kwargs)
            }
        }
        
        async with httpx.AsyncClient(timeout=300) as client:
            response = await client.post(
                f"{GOOGLE_API_URL}:generateContent",
                headers=self._get_headers(),
                json=payload
            )
            
            if response.status_code != 200:
                raise Exception(f"API Error {response.status_code}: {response.text[:500]}")
            
            result = response.json()
            return self._convert_to_openai_response(result, model)
    
    async def chat_completions_stream(self, model: str, messages: list, **kwargs) -> AsyncGenerator[str, None]:
        """流式聊天补全"""
        model = self._clean_model_name(model)
        
        contents = self._convert_messages(messages)
        
        payload = {
            "model": model,
            "project": self.project_id,
            "request": {
                "contents": contents,
                "generationConfig": self._build_generation_config(kwargs)
            }
        }
        
        async with httpx.AsyncClient(timeout=300) as client:
            async with client.stream(
                "POST",
                f"{GOOGLE_API_URL}:streamGenerateContent?alt=sse",
                headers=self._get_headers(),
                json=payload
            ) as response:
                if response.status_code != 200:
                    error = await response.aread()
                    raise Exception(f"API Error {response.status_code}: {error.decode()[:500]}")
                
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        try:
                            data = json.loads(line[6:])
                            chunk = self._convert_stream_chunk(data, model)
                            if chunk:
                                yield f"data: {json.dumps(chunk)}\n\n"
                        except:
                            pass
        
        yield "data: [DONE]\n\n"
    
    def _convert_messages(self, messages: list) -> list:
        """将 OpenAI 消息格式转换为 Gemini 格式"""
        contents = []
        system_text = ""
        
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            
            if role == "system":
                system_text = content
                continue
            
            gemini_role = "user" if role == "user" else "model"
            
            # 处理多模态内容
            if isinstance(content, list):
                parts = []
                for item in content:
                    if item.get("type") == "text":
                        parts.append({"text": item.get("text", "")})
                    elif item.get("type") == "image_url":
                        # 处理图片
                        url = item.get("image_url", {}).get("url", "")
                        if url.startswith("data:"):
                            # Base64 图片
                            import re
                            match = re.match(r"data:([^;]+);base64,(.+)", url)
                            if match:
                                parts.append({
                                    "inlineData": {
                                        "mimeType": match.group(1),
                                        "data": match.group(2)
                                    }
                                })
                contents.append({"role": gemini_role, "parts": parts})
            else:
                text = content
                if system_text and gemini_role == "user" and len(contents) == 0:
                    text = f"{system_text}\n\n{content}"
                    system_text = ""
                contents.append({"role": gemini_role, "parts": [{"text": text}]})
        
        return contents
    
    def _build_generation_config(self, kwargs: dict) -> dict:
        """构建生成配置"""
        config = {}
        
        if "temperature" in kwargs:
            config["temperature"] = kwargs["temperature"]
        if "max_tokens" in kwargs:
            config["maxOutputTokens"] = kwargs["max_tokens"]
        if "top_p" in kwargs:
            config["topP"] = kwargs["top_p"]
        if "stop" in kwargs:
            config["stopSequences"] = kwargs["stop"] if isinstance(kwargs["stop"], list) else [kwargs["stop"]]
        
        return config
    
    def _convert_to_openai_response(self, result: dict, model: str) -> dict:
        """将 Gemini 响应转换为 OpenAI 格式"""
        response_data = result.get("response", result)
        candidates = response_data.get("candidates", [])
        
        content = ""
        if candidates:
            parts = candidates[0].get("content", {}).get("parts", [])
            content = "".join(p.get("text", "") for p in parts)
        
        return {
            "id": f"chatcmpl-{id(result)}",
            "object": "chat.completion",
            "created": 0,
            "model": model,
            "choices": [{
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": content
                },
                "finish_reason": "stop"
            }],
            "usage": {
                "prompt_tokens": 0,
                "completion_tokens": 0,
                "total_tokens": 0
            }
        }
    
    def _convert_stream_chunk(self, data: dict, model: str) -> Optional[dict]:
        """将 Gemini 流式块转换为 OpenAI 格式"""
        response_data = data.get("response", data)
        candidates = response_data.get("candidates", [])
        
        if not candidates:
            return None
        
        parts = candidates[0].get("content", {}).get("parts", [])
        text = "".join(p.get("text", "") for p in parts)
        
        if not text:
            return None
        
        return {
            "id": f"chatcmpl-{id(data)}",
            "object": "chat.completion.chunk",
            "created": 0,
            "model": model,
            "choices": [{
                "index": 0,
                "delta": {
                    "content": text
                },
                "finish_reason": None
            }]
        }

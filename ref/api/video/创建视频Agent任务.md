# 创建视频Agent任务

Source: https://platform.minimaxi.com/docs/api-reference/video-agent-create

# 创建视频Agent任务

> 使用本接口创建视频Agent任务。



## OpenAPI

````yaml /api-reference/video/agent/api/openapi.json POST /v1/video_template_generation
openapi: 3.1.0
info:
  title: MiniMax API
  description: MiniMax video template generation API
  license:
    name: MIT
  version: 1.0.0
servers:
  - url: https://api.minimaxi.com
security:
  - bearerAuth: []
paths:
  /v1/video_template_generation:
    post:
      tags:
        - Video
      summary: Video Template Generation
      operationId: videoTemplateGeneration
      parameters:
        - name: Content-Type
          in: header
          required: true
          description: 请求体的媒介类型，请设置为 `application/json`，确保请求数据的格式为 JSON
          schema:
            type: string
            enum:
              - application/json
            default: application/json
      requestBody:
        description: ''
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/VideoTemplateGenerationReq'
        required: true
      responses:
        '200':
          description: ''
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/VideoTemplateGenerationResp'
components:
  schemas:
    VideoTemplateGenerationReq:
      type: object
      required:
        - template_id
      properties:
        template_id:
          type: string
          description: 视频模板的 ID。具体的 ID 和所需输入参见 [视频模板列表](/faq/video-agent-templates)。
        text_inputs:
          type: array
          description: 文本输入数组，用于填充模板中的文本部分，不同模板对此要求不同
          items:
            $ref: '#/components/schemas/TextInput'
        media_inputs:
          type: array
          description: 媒体输入数组（如图片），用于填充模板中的媒体部分，不同模板对此要求不同
          items:
            $ref: '#/components/schemas/MediaInput'
        callback_url:
          type: string
          description: >-
            接收任务状态更新通知的回调 URL。支持通过 `callback_url` 参数可以配置回调，以接收任务状态的更新的异步通知


            1. 地址验证：配置后，MiniMax 服务器会向 `callback_url` 发送一个 `POST` 请求，请求体中包含
            `challenge` 字段。服务端需要在 3 秒内原样返回该 `challenge` 值以完成验证


            2. 状态更新：验证成功后，每当任务状态变更时，MiniMax 都会向该 URL
            推送最新的任务状态。推送的数据结构与调用查询视频生成任务接口的响应体一致


            回调返回的`status`包括以下状态：

            - `processing` - 生成中

            - `success` - 成功

            - `failed` - 失败


            回调服务示例:

            ```python dark

            from fastapi import FastAPI, HTTPException, Request

            from fastapi.middleware.cors import CORSMiddleware

            import json


            app = FastAPI()


            @app.post("/get_callback")

            async def get_callback(request: Request):
                try:
                    json_data = await request.json()
                    challenge = json_data.get("challenge")
                    if challenge is not None:
                        # Verification request, return challenge as is
                        return {"challenge": challenge}
                    else:
                        # Callback request, handle your own logic here
                        # Example payload:
                        # {
                        #     "task_id": "115334141465231360",
                        #     "status": "Success",
                        #     "file_id": "205258526306433",
                        #     "base_resp": {
                        #         "status_code": 0,
                        #         "status_msg": "success"
                        #     }
                        # }
                        return {"status": "success"}
                except Exception as e:
                    raise HTTPException(status_code=500, detail=str(e))

            if __name__ == "__main__":
                import uvicorn
                uvicorn.run(
                    app,  # 必选
                    host="0.0.0.0",  # 必选
                    port=8000,  # 必选，端口可设置
                    # ssl_keyfile="yourname.yourDomainName.com.key", # 可选，看是否开启ssl
                    # ssl_certfile="yourname.yourDomainName.com.crt", # 可选，看是否开启ssl
                )
            ```
      example:
        template_id: '393769180141805569'
        media_inputs:
          - value: >-
              https://cdn.hailuoai.com/prod/2024-09-18-16/user/multi_chat_file/9c0b5c14-ee88-4a5b-b503-4f626f018639.jpeg
        text_inputs:
          - value: 狮子
    VideoTemplateGenerationResp:
      type: object
      properties:
        task_id:
          type: string
          description: 任务的唯一 ID，可用于后续查询任务状态
        base_resp:
          $ref: '#/components/schemas/BaseResp'
      example:
        task_id: '401047179385389059'
        base_resp:
          status_code: 0
          status_msg: success
    TextInput:
      type: object
      required:
        - value
      properties:
        value:
          type: string
          description: 具体的文本内容
    MediaInput:
      type: object
      required:
        - value
      properties:
        value:
          type: string
          description: |-
            图像文件。支持公网 URL 或 Base64 编码的 Data URL (`data:image/jpeg;base64,...`)。

            图片要求：
            - 格式：JPG, JPEG, PNG, WebP
            - 大小：小于 20MB
            - 尺寸：短边像素大于 300px
            - 宽高比：在 2:5 到 5:2 之间
    BaseResp:
      type: object
      description: 状态码及状态详情
      properties:
        status_code:
          type: integer
          format: int32
          description: |-
            状态码及其分别含义如下：

            `0`: 请求成功
            `1002`: 触发限流，请稍后再试
            `1004`: 账号鉴权失败，请检查 API-Key 是否填写正确
            `1008`: 账号余额不足
            `1026`: 文本涉及敏感内容，请调整
            `2013`: 传入参数异常，请检查入参是否按要求填写
            `2049`: 无效的api key，请检查api key

            更多内容可查看 [错误码查询列表](/api-reference/errorcode) 了解详情
        status_msg:
          type: string
          description: 具体错误详情
  securitySchemes:
    bearerAuth:
      type: http
      scheme: bearer
      bearerFormat: JWT
      description: |-
        `HTTP: Bearer Auth`
         - Security Scheme Type: http
         - HTTP Authorization Scheme: Bearer API_key，用于验证账户信息，可在 [账户管理>接口密钥](https://platform.minimaxi.com/user-center/basic-information/interface-key) 中查看。

````
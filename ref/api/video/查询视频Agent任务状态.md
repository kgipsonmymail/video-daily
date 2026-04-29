# 查询视频Agent任务状态

Source: https://platform.minimaxi.com/docs/api-reference/video-agent-query

# 查询视频Agent任务状态

> 使用本接口查询使用视频Agent生成视频的任务状态。



## OpenAPI

````yaml /api-reference/video/agent/api/openapi.json GET /v1/query/video_template_generation
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
  /v1/query/video_template_generation:
    get:
      tags:
        - Video
      operationId: queryVideoTemplateGenerationTask
      parameters:
        - name: task_id
          in: query
          required: true
          description: 待查询的任务 ID。只能查询当前账号创建的任务
          schema:
            type: string
          example: '401047179385389059'
      responses:
        '200':
          description: ''
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/QueryVideoTemplateGenerationTaskResp'
components:
  schemas:
    QueryVideoTemplateGenerationTaskResp:
      type: object
      properties:
        task_id:
          type: string
          description: 被查询的任务 ID
        status:
          $ref: '#/components/schemas/VideoProcessStatus'
        video_url:
          type: string
          description: 任务成功时返回。生成视频的下载链接。注意：下载链接有效期为 9 小时
        base_resp:
          $ref: '#/components/schemas/QueryBaseResp'
      example:
        task_id: '401047179385389059'
        status: Success
        video_url: https://cdn.hailuoai.com/prod/video_20250714_141232_cdc5ba74.mp4
        base_resp:
          status_code: 0
          status_msg: success
    VideoProcessStatus:
      type: string
      enum:
        - Preparing
        - Processing
        - Success
        - Fail
      description: |-
        任务状态，可能的值包括：

        - `Preparing` – 准备中
        - `Processing` – 生成中
        - `Success` – 成功
        - `Fail` – 失败
    QueryBaseResp:
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
            `1004`: 账号鉴权失败，请检查 api key是否填写正确
            `1026`: 输入内容涉及敏感内容l
            `1027`: 生成视频涉及敏感内容

            更多内容可查看 [错误码查询列表](/api-reference/errorcode) 了解详情
        status_msg:
          type: string
          description: 状态信息，成功时为 `success`
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
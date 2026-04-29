# 文本对话（Anthropic API 兼容）

Source: https://platform.minimaxi.com/docs/api-reference/text-chat-anthropic

# 文本对话（Anthropic API 兼容）

> 使用 Anthropic API 兼容格式接口调用 MiniMax 模型，支持角色扮演、多轮对话等对话场景。支持丰富的角色设定（system、user_system、group 等）和示例对话学习。



## OpenAPI

````yaml /api-reference/text/api/openapi-chat-anthropic.json POST /anthropic/v1/messages
openapi: 3.1.0
info:
  title: MiniMax Text API Anthropic
  description: >-
    MiniMax text generation API with support for chat completion and streaming
    output
  license:
    name: MIT
  version: 1.0.0
servers:
  - url: https://api.minimaxi.com
security:
  - bearerAuth: []
paths:
  /anthropic/v1/messages:
    post:
      tags:
        - Text Generation
      summary: Text Generation Anthropic
      operationId: chatCompletionAnthropic
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
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/CreateMessageReq'
            examples:
              Request:
                value:
                  model: MiniMax-M2.7
                  messages:
                    - role: user
                      content: 你好
              Stream:
                value:
                  model: MiniMax-M2.7
                  stream: true
                  messages:
                    - role: user
                      content: 你好
        required: true
      responses:
        '200':
          description: ''
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/CreateMessageResp'
              examples:
                Request:
                  value:
                    id: 06379dbe27b33d7c58d8410a8efe6394
                    type: message
                    role: assistant
                    model: MiniMax-M2.7
                    content:
                      - thinking: 用户用中文说"你好"，这是一个简单的问候。我应该用中文友好地回应。
                        signature: >-
                          ce704495524bad054531fe187e18b4a8d874a52fbb3923ce18fceace5e768ec9
                        type: thinking
                      - text: 你好！有什么我可以帮助你的吗？
                        type: text
                    usage:
                      input_tokens: 42
                      output_tokens: 30
                    stop_reason: end_turn
                    base_resp:
                      status_code: 0
                      status_msg: ''
                Stream:
                  value:
                    - type: message_start
                      message:
                        id: 06379e8c64a345d787539619216ee698
                        type: message
                        role: assistant
                        content: []
                        model: MiniMax-M2.7
                        stop_reason: null
                        stop_sequence: null
                        usage:
                          input_tokens: 0
                          output_tokens: 0
                        service_tier: standard
                    - type: ping
                    - type: content_block_start
                      index: 0
                      content_block:
                        type: thinking
                        thinking: ''
                    - type: content_block_delta
                      index: 0
                      delta:
                        type: thinking_delta
                        thinking: 用户
                    - type: content_block_delta
                      index: 0
                      delta:
                        type: thinking_delta
                        thinking: 用中文说"你好"，这是一个简单的问候。我应该用中文友好地回应。
                    - type: content_block_delta
                      index: 0
                      delta:
                        type: signature_delta
                        signature: >-
                          ce704495524bad054531fe187e18b4a8d874a52fbb3923ce18fceace5e768ec9
                    - type: content_block_stop
                      index: 0
                    - type: content_block_start
                      index: 1
                      content_block:
                        type: text
                        text: ''
                    - type: content_block_delta
                      index: 1
                      delta:
                        type: text_delta
                        text: |-


                          你好！有什么我可以帮助你的吗？
                    - type: content_block_stop
                      index: 1
                    - type: message_delta
                      delta:
                        stop_reason: end_turn
                      usage:
                        input_tokens: 39
                        output_tokens: 29
                    - type: message_stop
            text/event-stream:
              schema:
                $ref: '#/components/schemas/StreamEvent'
              examples:
                Stream:
                  value:
                    - type: message_start
                      message:
                        id: 06379e8c64a345d787539619216ee698
                        type: message
                        role: assistant
                        content: []
                        model: MiniMax-M2.7
                        stop_reason: null
                        stop_sequence: null
                        usage:
                          input_tokens: 0
                          output_tokens: 0
                        service_tier: standard
                    - type: ping
                    - type: content_block_start
                      index: 0
                      content_block:
                        type: thinking
                        thinking: ''
                    - type: content_block_delta
                      index: 0
                      delta:
                        type: thinking_delta
                        thinking: 用户
                    - type: content_block_delta
                      index: 0
                      delta:
                        type: thinking_delta
                        thinking: 用中文说"你好"，这是一个简单的问候。我应该用中文友好地回应。
                    - type: content_block_delta
                      index: 0
                      delta:
                        type: signature_delta
                        signature: >-
                          ce704495524bad054531fe187e18b4a8d874a52fbb3923ce18fceace5e768ec9
                    - type: content_block_stop
                      index: 0
                    - type: content_block_start
                      index: 1
                      content_block:
                        type: text
                        text: ''
                    - type: content_block_delta
                      index: 1
                      delta:
                        type: text_delta
                        text: |-


                          你好！有什么我可以帮助你的吗？
                    - type: content_block_stop
                      index: 1
                    - type: message_delta
                      delta:
                        stop_reason: end_turn
                      usage:
                        input_tokens: 39
                        output_tokens: 29
                    - type: message_stop
components:
  schemas:
    CreateMessageReq:
      type: object
      required:
        - model
        - messages
      properties:
        model:
          type: string
          description: 模型 ID
          enum:
            - MiniMax-M2.7
            - MiniMax-M2.7-highspeed
            - MiniMax-M2.5
            - MiniMax-M2.1
        system:
          description: 设定模型的角色和行为
          oneOf:
            - type: string
              description: 纯文本系统提示词
            - type: array
              description: 内容块数组格式的系统提示词
              items:
                type: object
                properties:
                  type:
                    type: string
                    enum:
                      - text
                    description: 内容块类型
                  text:
                    type: string
                    description: 文本内容
                required:
                  - type
                  - text
        messages:
          type: array
          description: 包含对话历史的消息列表
          items:
            $ref: '#/components/schemas/Message'
        stream:
          type: boolean
          description: 是否使用流式传输，默认为 `false`。设置为 `true` 后，响应将分批返回
          default: false
        max_tokens:
          type: integer
          format: int64
          description: >-
            指定生成内容长度的上限（Token 数），上限为 2048。超过上限的内容会被截断。如果生成因 `length`
            原因中断，请尝试调高此值
          minimum: 1
        temperature:
          type: number
          format: double
          description: >-
            温度系数，影响输出随机性，取值范围 (0, 1]，`MiniMax-M2.7` 模型默认值为
            1.0。值越高，输出越随机；值越低，输出越确定
          minimum: 0
          exclusiveMinimum: 0
          maximum: 1
          default: 1
        top_p:
          type: number
          format: double
          description: 采样策略，影响输出随机性，取值范围 (0, 1]，`MiniMax-M2.7` 模型默认值为 0.95
          minimum: 0
          exclusiveMinimum: 0
          maximum: 1
          default: 0.95
    CreateMessageResp:
      type: object
      properties:
        id:
          type: string
          description: 本次响应的唯一 ID
        type:
          type: string
          description: 对象类型，固定为 `message`
          enum:
            - message
        role:
          type: string
          description: 角色，固定为 `assistant`
          enum:
            - assistant
        model:
          type: string
          description: 本次请求使用的模型 ID
        content:
          type: array
          description: 响应内容块列表
          items:
            $ref: '#/components/schemas/ContentBlock'
        stop_reason:
          type: string
          description: |-
            生成停止的原因：
            - `end_turn`: 模型自然结束
            - `max_tokens`: 达到 `max_tokens` 上限
            - `stop_sequence`: 命中停止序列
          enum:
            - end_turn
            - max_tokens
            - stop_sequence
        usage:
          $ref: '#/components/schemas/Usage'
        base_resp:
          type: object
          description: 错误状态码和详情
          properties:
            status_code:
              type: integer
              format: int64
              description: |-
                状态码

                - `1000`: 未知错误
                - `1001`: 请求超时
                - `1002`: 触发限流
                - `1004`: 鉴权失败
                - `1008`: 余额不足
                - `1013`: 服务内部错误
                - `1027`: 输出内容错误
                - `1039`:  Token 超出限制
                - `2013`: 参数错误

                更多内容可查看 [错误码查询列表](/api-reference/errorcode) 了解详情
            status_msg:
              type: string
              description: 错误详情
    StreamEvent:
      type: object
      description: ''
      required:
        - type
      properties:
        type:
          type: string
          description: |-
            事件类型：
            - `message_start`: 消息开始，包含完整的消息元数据
            - `ping`: 心跳事件
            - `content_block_start`: 内容块开始
            - `content_block_delta`: 内容块增量更新
            - `content_block_stop`: 内容块结束
            - `message_delta`: 消息级别的增量更新（如 stop_reason）
            - `message_stop`: 消息结束
          enum:
            - message_start
            - ping
            - content_block_start
            - content_block_delta
            - content_block_stop
            - message_delta
            - message_stop
        message:
          type: object
          description: 消息对象（`type` 为 `message_start` 时返回）
          properties:
            id:
              type: string
              description: 消息的唯一 ID
            type:
              type: string
              enum:
                - message
            role:
              type: string
              enum:
                - assistant
            content:
              type: array
              description: 内容块列表，初始为空数组
              items:
                $ref: '#/components/schemas/ContentBlock'
            model:
              type: string
              description: 模型 ID
            stop_reason:
              type: string
              nullable: true
              description: 停止原因，流式开始时为 null
            stop_sequence:
              type: string
              nullable: true
              description: 停止序列，流式开始时为 null
            usage:
              $ref: '#/components/schemas/Usage'
            service_tier:
              type: string
              description: 服务层级
        index:
          type: integer
          description: >-
            内容块的索引（`content_block_start`、`content_block_delta`、`content_block_stop`
            时返回）
        content_block:
          $ref: '#/components/schemas/ContentBlock'
          description: 内容块对象（`type` 为 `content_block_start` 时返回）
        delta:
          type: object
          description: 增量更新内容（`content_block_delta` 或 `message_delta` 时返回）
          properties:
            type:
              type: string
              description: 增量类型，如 `text_delta`
            text:
              type: string
              description: 增量文本内容
            stop_reason:
              type: string
              description: 停止原因（`message_delta` 时返回）
              enum:
                - end_turn
                - max_tokens
                - stop_sequence
        usage:
          $ref: '#/components/schemas/Usage'
          description: Token 使用情况（`message_delta` 时返回）
    Message:
      type: object
      required:
        - role
        - content
      properties:
        role:
          type: string
          enum:
            - user
            - assistant
            - user_system
            - group
            - sample_message_user
            - sample_message_ai
          description: |-
            消息发送者的角色
            - `user`: 用户的输入
            - `assistant`: 模型的历史回复
            - `user_system`: 设定用户的角色和人设
            - `group`: 对话的名称
            - `sample_message_user`: 示例的用户输入
            - `sample_message_ai`: 示例的模型输出
        content:
          description: 消息内容，支持纯文本字符串或内容块数组
          oneOf:
            - type: string
              description: 纯文本消息
            - type: array
              description: 内容块数组，支持文本和思考等内容块
              items:
                $ref: '#/components/schemas/ContentBlock'
    ContentBlock:
      type: object
      required:
        - type
      properties:
        type:
          type: string
          description: |-
            内容块类型：
            - `text`: 文本内容
            - `thinking`: 模型思考过程
          enum:
            - text
            - thinking
        text:
          type: string
          description: 文本内容（当 `type` 为 `text` 时）
        thinking:
          type: string
          description: 模型的思考过程内容（当 `type` 为 `thinking` 时）
        signature:
          type: string
          description: 思考内容的签名（当 `type` 为 `thinking` 时）
    Usage:
      type: object
      description: 本次请求的 Token 使用情况
      properties:
        input_tokens:
          type: integer
          description: 输入消耗的 Token 数
        output_tokens:
          type: integer
          description: 输出消耗的 Token 数
  securitySchemes:
    bearerAuth:
      type: http
      scheme: bearer
      bearerFormat: JWT
      description: |-
        `HTTP: Bearer Auth`
         - Security Scheme Type: http
         - HTTP Authorization Scheme: Bearer API_key，用于验证账户信息，可在 [账户管理>接口密钥](https://platform.minimaxi.com/user-center/basic-information/interface-key) 中查看

````
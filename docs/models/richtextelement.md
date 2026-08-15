# RichTextElement

One node in Pumble's rich-text block structure. The full grammar is
large (Slack-like); only top-level fields are typed here.



## Fields

| Field                                                        | Type                                                         | Required                                                     | Description                                                  | Example                                                      |
| ------------------------------------------------------------ | ------------------------------------------------------------ | ------------------------------------------------------------ | ------------------------------------------------------------ | ------------------------------------------------------------ |
| `type`                                                       | *Optional[str]*                                              | :heavy_minus_sign:                                           | N/A                                                          | text                                                         |
| `text`                                                       | *Optional[str]*                                              | :heavy_minus_sign:                                           | N/A                                                          | Hello world                                                  |
| `elements`                                                   | List[[models.RichTextElement](../models/richtextelement.md)] | :heavy_minus_sign:                                           | N/A                                                          |                                                              |
| `highlight`                                                  | *Optional[str]*                                              | :heavy_minus_sign:                                           | Present on search-hit blocks to indicate matching text.      | Hello                                                        |
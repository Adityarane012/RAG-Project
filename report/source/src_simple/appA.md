# Appendix A: UML Activity Diagrams

@fig:a_pipeline shows the whole path of one question. @fig:a_verify shows how one model is checked, and @fig:a_size shows the size rule. The diagrams use standard UML activity-diagram notation and were drawn with PlantUML from the text files in `report/source/uml`.

::: fig a_pipeline w=5.3
uml_pipeline.png
UML activity diagram of the question pipeline.
:::

::: fig a_verify w=11
uml_verify.png
UML activity diagram of the check for one model: one result for each requested rule, then the combined result.
:::

::: fig a_size w=12
uml_size.png
UML activity diagram of the size rule: the exact total of the main weight files, unknown if there is any doubt.
:::

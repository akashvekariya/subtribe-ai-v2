// BAML Generator Configuration
// Generates Python/Pydantic client code from BAML definitions

generator target {
    // Valid values: "python/pydantic", "typescript", "ruby/sorbet", "rest/openapi"
    output_type "python/pydantic"

    // Where the generated code will be saved (relative to baml_src/)
    output_dir "../baml_client"

    // The version of the BAML package you have installed
    version "0.216.0"

    // Valid values: "sync", "async"
    // This controls what `b.FunctionName()` will be (sync or async).
    default_client_mode sync
}

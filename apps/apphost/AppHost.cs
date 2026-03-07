using Aspire.Hosting.JavaScript;
using Aspire.Hosting.Python;

var builder = DistributedApplication.CreateBuilder(args);

var api = builder.AddUvicornApp("api", "..\\api", "app.main:app")
    .WithPip()
    .WithExternalHttpEndpoints()
    .WithHttpHealthCheck("/health");

builder.AddJavaScriptApp("web", "..\\web")
    .WithHttpEndpoint(port: 3000, env: "PORT")
    .WithExternalHttpEndpoints()
    .WithReference(api)
    .WaitFor(api)
    .WithEnvironment("NEXT_PUBLIC_API_BASE_URL", "")
    .WithEnvironment("API_BASE_URL", api.GetEndpoint("http"))
    .WithEnvironment("MEAL_PLANNER_DEV_USER_ID", "dev-user-1")
    .WithEnvironment("MEAL_PLANNER_DEV_USER_EMAIL", "ashley@example.com")
    .WithEnvironment("MEAL_PLANNER_DEV_USER_NAME", "Ashley Hollis")
    .WithEnvironment("MEAL_PLANNER_DEV_ACTIVE_HOUSEHOLD_ID", "household-local")
    .WithEnvironment("MEAL_PLANNER_DEV_ACTIVE_HOUSEHOLD_NAME", "Local Household")
    .WithEnvironment("MEAL_PLANNER_DEV_ACTIVE_HOUSEHOLD_ROLE", "owner");

builder.Build().Run();

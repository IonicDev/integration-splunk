Integration With Splunk
===============

Here we offer a method of using custom scripting to poll the Ionic Download API and index its responses into Splunk.

To understand more about this integration, first read [Ionic's example integration page on Splunk](https://dev.ionic.com/integrations/splunk_rest_api.html).

## Configuration
The bulk of configuration instructions can be found in the [Splunk documentation](http://docs.splunk.com/Documentation/AddonBuilder/2.1.2/UserGuide/ConfigureDataCollectionAdvanced).
When configuring the "Data Input Parameters", consult the following table for parameters that are required for this script to operate properly.

| Parameter | Description | Example Value |
| --------- | ----------- | ------------- |
| `api_environment` | The hostname to use for querying. | `api.ionic.com` |
| `api_user_name` | User name of API-access account. | `api_user@company.com` |
| `api_user_password` | Password of API-access account. | `api_user_pass` |
| `tenant_id` | Tenant ID of tenant that the API-access account is registered under. | `555555555555555555555555` |
| `start_time` | Timestamp at which to begin querying data for. | `20171001-10:00` |
| `object_type` | Type of data to query for.  | `key_requests,arm` (comma-delimited for multiple object types) |

> NOTE: For more details on valid values for `object_type` or the format of `start_time`, please visit the
> [Ionic Download API documentation](https://dev.ionic.com/management-api/download/download-intro.html).

The Ionic Download API provides the ability to paginate through your tenant's data, so we make use of this here.
The included `forwarder.py` script uses the input parameters to construct an initial request to send to the Ionic Download API, 
 after which it will only use URIs extracted from the response's "Link" header for subsequent requests.
If there is no available URI in the response's "Link" header (or the header is missing), the code will sleep before retrying the previous request.
The most likely cause for this behavior is that it has caught up to the current time and must wait for data to become available. We recommend 15 minutes,
 but you may modify the value of `wait_to_retry_sec` in `forwarder.py` to alter this behavior.

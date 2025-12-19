# Release Notes

## v0.5.x series

The goal of this series is to bring support for Vendor up to Django v5.2+ (older versions will no longer be supported). The previous version was getting outdatated and needed a refresh. No major code cleanup was done other than to check for compatibility and make sure tests pass.

We also made sure the stripe dependencies were updated and tested. If people need it, we will also look to updating Authorize.Net.

## v0.6.x series

This will be a refactor, looking to streamline the code that has grown a little too much. This version may introduce breaking changes so it's a good idea to lock your project to the v0.5.x if you want to make sure you don't pick them up before you are ready.

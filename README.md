<div align="center" markdown="1">
Open source app specifically designated for investing in real estate assets.
</div>

## Introduction

Realestate Account could be managed by an individual or an entity, and funds in this account would be used for acquiring, managing, and selling real estate properties.

## Installation

### Manual Installation

1. Add Realestate Account app to your bench.
  ```
  bench get-app realestate_account https://github.com/beingeek/realestate_management.git --branch main
  ```
2. Install the app on the required site.
  ```
  bench --site sitename install-app realestate_management
  ```

### Update App
1. Update your app in the app directory.

  ```
  git pull
  ```
 2. Migrate the app to required site.

   ```
   $ bench --site sitename migrate
   ```
  

This document is specifically about using pysystemtrade for *live production trading*. 

*This is NOT a complete document, and is currently a work in progress - any in many cases a series of thoughts about design intent rather than a fully featured specificiation. It is not possible to run a full production system with pysystemtrade at present*

Ultimately this will include:

1. Getting prices
2. Generating desired trades
3. Executing trades
4. Getting accounting information

Related documents:

- [Storing futures and spot FX data](/docs/futures.md)
- [Main user guide](/docs/userguide.md)
- [Connecting pysystemtrade to interactive brokers](/docs/IB.md)

*IMPORTANT: Make sure you know what you are doing. All financial trading offers the possibility of loss. Leveraged trading, such as futures trading, may result in you losing all your money, and still owing more. Backtested results are no guarantee of future performance. No warranty is offered or implied for this software. I can take no responsibility for any losses caused by live trading using pysystemtrade. Use at your own risk.*

Table of Contents
=================

   * [Quick start guide](#quick-start-guide)
   * [Overview of a production system](#overview-of-a-production-system)
   * [Implementation options](#implementation-options)
      * [Automatation options](#automatation-options)
      * [Machines, containers and clouds](#machines-containers-and-clouds)
      * [Backup machine](#backup-machine)
      * [Multiple systems](#multiple-systems)
   * [Code and configuration management](#code-and-configuration-management)
         * [Managing your seperate directories of code and configuration](#managing-your-seperate-directories-of-code-and-configuration)
         * [Managing your private directory](#managing-your-private-directory)
   * [Finalise your backtest configuration](#finalise-your-backtest-configuration)
   * [Linking to a broker](#linking-to-a-broker)
   * [Other data sources](#other-data-sources)
   * [Data storage](#data-storage)
      * [Data backup](#data-backup)
         * [Mongo data](#mongo-data)
         * [Mongo / csv data](#mongo--csv-data)
   * [Echoes, Logging, diagnostics and reporting](#echoes-logging-diagnostics-and-reporting)
      * [Echos: stdout output](#echos-stdout-output)
         * [Cleaning old echo files](#cleaning-old-echo-files)
      * [Logging](#logging)
         * [Adding logging to your code](#adding-logging-to-your-code)
         * [Getting log data back](#getting-log-data-back)
         * [Cleaning old logs](#cleaning-old-logs)
      * [Reporting](#reporting)
         * [Roll report (Daily)](#roll-report-daily)
   * [Scripts](#scripts)
      * [Production system components](#production-system-components)
         * [Get spot FX data from interactive brokers, write to MongoDB (Daily)](#get-spot-fx-data-from-interactive-brokers-write-to-mongodb-daily)
         * [Update sampled contracts (Daily)](#update-sampled-contracts-daily)
         * [Update futures contract historical price data (Daily)](#update-futures-contract-historical-price-data-daily)
         * [Update multiple and adjusted prices (Daily)](#update-multiple-and-adjusted-prices-daily)
         * [Roll adjusted prices (whenever required)](#roll-adjusted-prices-whenever-required)
         * [Run an updated backtest system (overnight) for a single strategy](#run-an-updated-backtest-system-overnight-for-a-single-strategy)
      * [Ad-hoc diagnostics](#ad-hoc-diagnostics)
         * [Recent FX prices](#recent-fx-prices)
         * [Recent futures contract prices (FIX ME TO DO)](#recent-futures-contract-prices-fix-me-to-do)
         * [Recent multiple prices (FIX ME TO DO)](#recent-multiple-prices-fix-me-to-do)
         * [Recent adjusted prices (FIX ME TO DO)](#recent-adjusted-prices-fix-me-to-do)
         * [Roll information](#roll-information)
         * [Examine pickled backtest state object](#examine-pickled-backtest-state-object)
      * [Housekeeping](#housekeeping)
         * [Delete old pickled backtest state objects](#delete-old-pickled-backtest-state-objects)
         * [Clean up old log files](#clean-up-old-log-files)
         * [Truncate echo log files](#truncate-echo-log-files)
   * [Scheduling](#scheduling)
      * [Issues to consider when constructing the schedule](#issues-to-consider-when-constructing-the-schedule)
      * [A suggested schedule in pseudocode](#a-suggested-schedule-in-pseudocode)
      * [Formal list of scheduled tasks](#formal-list-of-scheduled-tasks)
      * [Choice of scheduling systems](#choice-of-scheduling-systems)
         * [Linux cron](#linux-cron)
         * [Windows task scheduler](#windows-task-scheduler)
         * [Python](#python)
         * [Manual system](#manual-system)
   * [Production system concepts](#production-system-concepts)
      * [Configuration files](#configuration-files)
         * [Private config](#private-config)
         * [System defaults](#system-defaults)
         * [Strategy config](#strategy-config)
      * [Strategies](#strategies)
   * [Production system data and data flow](#production-system-data-and-data-flow)
   * [Production system classes](#production-system-classes)
      * [Data blobs and the classes that feed on them](#data-blobs-and-the-classes-that-feed-on-them)
      * [Reporting and diagnostics](#reporting-and-diagnostics)

Created by [gh-md-toc](https://github.com/ekalinin/github-markdown-toc)



# Quick start guide

This quick start guide assumes the following:

- you are running on a linux box with a minimal distro installation
- you are using interactive brokers 
- you are storing data using mongodb
- you have a backtest that you are happy with
- you are happy to store your data and configuration in the /private directory of your pysystemtrade installation

You need to:

- Prerequisites:
    - Install [git](https://git-scm.com/book/en/v2/Getting-Started-Installing-Git), install or update [python3](https://docs.python-guide.org/starting/install3/linux/). You may also find a simple text editor (like emacs) is useful for fine tuning, and if you are using a headless server then [x11vnc](http://www.karlrunge.com/x11vnc/) is helpful.
    - Add the following environment variables to your .profile: (feel free to use other directories):
        - MONGO_DATA=/home/user_name/data/mongodb/
        - PYSYS_CODE=/home/user_name/pysystemtrade
        - SCRIPT_PATH=/home/user_name/pysystemtrade/sysproduction/linux/scripts
        - ECHO_PATH=/home/user/echos
        - MONGO_BACKUP_PATH=/media/shared_network/drive/mongo_backup
    - Create the following directories (again use other directories if you like, but you must modify the .profile above)
        - '/home/user_name/data/mongodb/'
        - '/home/user_name/echos/'
    - Install the pysystemtrade package, and install or update, any dependencies in directory $PYSYS_CODE (it's possible to put it elsewhere, but you will need to modify the environment variables listed above). If using git clone from your home directory this should create the directory '/home/user_name/pysystemtrade/'
    - [Set up interactive brokers](/docs/IB.md), download and install their python code, and get a gateway running.
    - [Install mongodb](https://docs.mongodb.com/manual/administration/install-on-linux/)
    - create a file 'private_config.yaml' in the private directory of [pysystemtrade](#/private)
    - [check a mongodb server is running with the right data directory](/docs/futures.md#mongo-db) command line: `mongod --dbpath $MONGO_DATA`
    - launch an IB gateway (this could be done automatically depending on your security setup)
- FX data:
    - [Initialise the spot FX data in MongoDB from .csv files](/sysinit/futures/repocsv_spotfx_prices.py) (this will be out of date, but you will update it in a moment)
    - Check that you have got spot FX data present: command line:`. /pysystemtrade/sysproduction/linux/scripts/read_fx_prices`
    - Update the FX price data in MongoDB using interactive brokers: command line:`. /home/your_user_name/workspace3/pysystemtrade/sysproduction/linux/scripts/update_fx_prices`
- Instrument configuration:
    - Set up futures instrument configuration using this script [instruments_csv_mongo.py](/sysinit/futures/instruments_csv_mongo.py).
- Roll calendars:
    - For *roll configuration* we need to initialise by running the code in this file [roll_parameters_csv_mongo.py](/sysinit/futures/roll_parameters_csv_mongo.py).
    - Create roll calendars for each instrument you are trading. Assuming you are happy to infer these from the supplied data [use this script](/sysinit/futures/rollcalendars_from_providedcsv_prices.py)
- Futures contract prices:
    - [If you have a source of individual futures prices, then backfill them into the Arctic database](/docs/futures.md#get_historical_data)
- Adjusted futures prices:
    - Create 'multiple prices' in Arctic. Assuming you have prices in Artic and roll calendars in csv use [this script](/sysinit/futures/multipleprices_from_arcticprices_and_csv_calendars_to_arctic.py). I recommend *not* writing the multiple prices to .csv, so that you can compare the legacy .csv data with the new prices
    - Create adjusted prices. Assuming you have multiple prices in Arctic use [this script](/sysinit/futures/adjustedprices_from_mongo_multiple_to_mongo.py)
- Live production backtest:
    - Create a yamal config file to run the live production 'backtest'. For speed I recommend you do not estimate parameters, but use fixed parameters, using the [yaml_config_with_estimated_parameters method of systemDiag](/systems/diagoutput.py) function to output these to a .yaml file.

- Scheduling:
    - Initialise the [supplied crontab](/sysproduction/linux/crontab). Note if you have put your code or echos somewhere else you will need to modify the directory references at the top of the crontab.
    - All scripts executable by the crontab need to be executable, so do the following: `cd $SCRIPT_PATH` ; `sudo chmod +x *.*`


Before trading, and each time you restart the machine you should:

- [check a mongodb server is running with the right data directory](/docs/futures.md#mongo-db) command line: `mongod --dbpath $MONGO_DATA` (the supplied crontab should do this)
- launch an IB gateway (this could [be done automatically](https://github.com/ib-controller/ib-controller) depending on your security setup)

When trading you will need to do the following

- Check reports TO DO LINK TO EACH
- Roll instruments TO DO LINK
- Ad-hoc diagnostics TO DO LINK


# Overview of a production system

Here are the steps you need to follow to set up a production system. I assume you already have a backtested system in pysystemtrade, with appropriate python libraries etc.

1. Consider your implementation options
2. Ensure you have a private area for your system code and configuration
3. Finalise and store your backtested system configuration
4. If you want to automatically execute, or get data from a broker, then set up a broker 
5. Set up any other data sources you need.
6. Set up a database for storage, including a backup
7. Have a strategy for reporting, diagnostics, and logs
8. Write some scripts to kick off processes to: get data, get accounting information, calculate optimal positions, execute trades, run reports.
9. Schedule your scripts to run regularly
10. Regularly monitor your system, and deal with any problems


# Implementation options

Standard implementation for pysystemtrade is a fully automated system running on a single local machine. In this section I briefly describe some alternatives you may wish to consider.

My own implementation runs on a Linux machine, and some of the implementation details in this document are Linux specific. Windows and Mac users are welcome to contribute with respect to any differences.

## Automatation options

You can run pysystemtrade as a fully automated system, which does everything from getting prices through to executing orders. But other patterns make sense. In particular you may wish to do your trading manually, after pulling in prices and generating optimal positions manually. It will also possible to trade manually, but allow pysystemtrade to pick up your fills from the broker rather than entering them manually.

## Machines, containers and clouds

Pysystemtrade can be run locally in the normal way, on a single machine. But you may also want to consider containerisation (see [my blog post](https://qoppac.blogspot.com/2017/01/playing-with-docker-some-initial.html)), or even implementing on AWS or another cloud solution. You could also spread your implemetation across several local machines.

If spreading your implementation across several machines bear in mind:

- Interactive brokers
   - interactive brokers Gateway will need to have the ip address of all relevant machines that connect to it in the whitelist
   - you will need to modify the `private_config.yaml` system configuration file so it connects to a different IP address `ib_ipaddress: '192.168.0.10'`
- Mongodb
   - Add an ip address the `bind_ip` line in the `/etc/mongod.conf` file to allow connections from other machines `eg bind_ip=localhost, 192.168.0.10`
   - you will need to modify the `private_config.yaml` system configuration file so it connects to a different IP address `mongo_host: 192.168.0.13`
   - you may want to enforce [further security protocol](https://docs.mongodb.com/manual/administration/security-checklist/)

## Backup machine

If you are running your implementation locally, or on a remote server that is not a cloud, then you should seriously consider a backup machine. The backup machine should have an up to date environment containing all the relevant applications, code and libaries, and on a regular basis you should update the local data stored on that machine (see INSERT BACKUP LINK). The backup machine doesn't need to be turned on at all times, unless you are trading in such a way that a one hour period without trading would be critical (in my experience, one hour is the maximum time to get a backup machine on line assuming the code is up to date, and the data is less than 24 hours stale). I also encourage you to perform a scheduled 'failover' on regular basis: stop the live machine running (best to do this at a weekend), copy across any data to the backup machine, start up the backup machine. The live machine then becomes the backup.

## Multiple systems

You may want to run multiple trading systems on a single machine. Common use cases are:

- You want different systems for different asset classes
- You want to run relative value systems *
- You want different systems for different time frames (eg intra day and slower trading) *
- You want to run the same system, but for different trading accounts
- You want a paper trading and live trading system

* for these cases I plan to implement functionality in pysystemtrade so that it can handle them in the same system.

To handle this I suggest having multiple copies of the pysystemtrade environment. You will have a single crontab, but you will need multiple script, echos and other directories. You will need to change the private config file so it points to different mongo_db database names. If you don't want multiple copies of certain data (eg prices) then you should hardcode the database_name in the relevant files whenever a connection is made eg mongo_db = mongoDb(database_name='whatever'). See storing futures and spot FX data for more detail. Finally you should set the field ib_idoffset in the private config file so that there is no chance of duplicate clientid connections; setting one system to have an id offset of 1, the next offset 1000, and so on should be sufficient.

Finally you should set the field `ib_idoffset` in the [private config file](private.private_config.yaml) so that there is no chance of duplicate clientid connections; setting one system to have an id offset of 1, the next offset 1000, and so on should be sufficient.

# Code and configuration management

Your trading strategy will consist of pysystemtrade, plus some specific configuration files, plus possibly some bespoke code. You can eithier implement this as:

- seperate environment, pulling in pysystemtrade as a 'yet another library'
- everything in pysystemtrade, with all specific code and configuration in the 'private' directory that is excluded from git uploads.

Personally I prefer the latter as it makes a neat self contained unit, but this is up to you.

### Managing your seperate directories of code and configuration

I strongly recommend that you use a code repo system or similar to manage your non pysystemtrade code and configuration. Since code and configuration will mostly be in text (or text like) yaml files a code repo system like git will work just fine. I do not recommend storing configuration in database files that will need to be backed up seperately, because this makes it more complex to store old configuration data that can be archived and retrieved if required. 

### Managing your private directory

Since the private directory is excluded from the git system (since you don't want it appearing on github!), you need to ensure it is managed seperately. I use a script which I run in lieu of a normal git add/ commit / push cycle:

```
# pass commit quote as an argument
# For example:
# . commit "this is a commit description string"
#
# copy the contents of the private directory to another, git controlled, directory
#
# we use rsync so we can exclude the git directory; which will screw things up as there is already one there
#
rsync -av ~/pysystemtrade/private/ ~/private --exclude .git
#
# git add/commit/push cycle on the main pysystemtrade directory
#
cd ~/pysystemtrade/
git add *
git commit -m "$1"
git push
#
# git add/commit/push cycle on the copied private directory
#
cd ~/private/
git add *
git commit -m "$1"
git push
```

A second script is run instead of a git pull:

```
# git pull within git controlled private directory copy
cd ~/private/
git pull
# copy the updated contents of the private directory to pysystemtrade private directory
# use rsync to avoid overwriting git metadata
rsync -av ~/private/ ~/pysystemtrade/private --exclude .git
# git pull from main pysystemtrade github repo
cd ~/pysystemtrade/
git pull
```

I use a local git repo for my private directory. Github are now offering free private repos, so that is another option.


# Finalise your backtest configuration

You can just re-run a daily backtest to generate your positions. This will probably mean that you end up refitting parameters like instrument weights and forecast scalars. This is pointless, a waste of time, and potentially dangerous. Instead I'd suggest using fixed values for all fitted parameters in a live trading system.

The following convenience function will take your backtested system, and create a dict which includes fixed values for all estimated parameters:

```python
# Assuming futures_system already contains a system which has estimated values
from systems.diagoutput import systemDiag

sysdiag = systemDiag(system)
sysdiag.yaml_config_with_estimated_parameters('someyamlfile.yaml',
                                              attr_names=['forecast_scalars',
                                                                  'forecast_weights',
                                                                  'forecast_div_multiplier',
                                                                  'forecast_mapping',
                                                                  'instrument_weights',
                                                                  'instrument_div_multiplier'])

```

Change the list of attr_names depending on what you want to output. You can then merge the resulting .yaml file into your simulation .yaml file. Don't forget to turn off the flags for `use_forecast_div_mult_estimates`,`use_forecast_scale_estimates`,`use_forecast_weight_estimates`,`use_instrument_div_mult_estimates`, and `use_instrument_weight_estimates`.  You don't need to change flag for forecast mapping, since this isn't done by default.

# Strategy configuration

FIX ME

# Linking to a broker

You are probably going to want to link your system to a broker, to do one or more of the following things:

- get prices 
- get account value and profitability
- do trades
- get trade fills

... although one or more of these can also be done manually.

You should now read [connecting pysystemtrade to interactive brokers](/docs/IB.md). 


# Other data sources

You might get all your data from your broker, but there are good reasons to get data from other sources as well:

- multiple sources can improve accuracy 
- multiple sources can provide redundancy in case of feed issues
- you can't get the relevant data from your broker
- the relevant data is cheaper elsewhere

You should now read [getting and storing futures and spot FX data](/docs/futures.md).


# Data storage

Various kinds of data files are used by the pysystemtrade production system. Broadly speaking they fall into the following categories:

- accounting (calculations of profit and loss)
- diagnostics
- prices (see [storing futures and spot FX data](/docs/futures.md))
- positions
- other state and control information
- static configuration files

The default option is to store these all into a mongodb database, except for configuration files which are stored as .yaml and .csv files.

## Data backup

### Mongo data

Assuming that you are using the default mongob for storing, then I recommend using [mongodump](https://docs.mongodb.com/manual/reference/program/mongodump/#bin.mongodump) on a daily basis to back up your files. Other more complicated alternatives are available (see the [official mongodb man page](https://docs.mongodb.com/manual/core/backups/)). You may also want to do this if you're transferring your data to e.g. a new machine.

To avoid conflicts you should [schedule](#scheduling) your backup during the 'deadtime' for your system (see scheduling).

FIX ME ADD BACKUP TO CRONTAB


Linux:
```
# dumps everything into dump directory
# make sure a mongo-db instance is running with correct directory, but ideally without any load; command line: `mongod --dbpath $MONGO_DATA`
mongodump -o ~/dump/

# copy dump directory to another machine or drive. This will create a directory $MONGO_BACKUP_PATH/dump/
cp -rf ~/dump/* $MONGO_BACKUP_PATH
```

Then to restore, from a linux command line:
```
cp -rf $MONGO_BACKUP_PATH/dump/ ~
# Now make sure a mongo-db instance is running with correct directory
# If required delete any existing instances of the databases. If you don't do this the results may be unpredictable...
mongo
# This starts a mongo client 
> show dbs
admin              0.000GB
arctic_production  0.083GB
config             0.000GB
local              0.000GB
meta_db            0.000GB
production         0.000GB
# Most likely we want to remove 'production' and 'arctic_production'
> use production
> db.dropDatabase()
> use arctic_production
> db.dropDatabase()
> exit
# Now we run the restore (back on the linux command line)
mongorestore 
```


### Mongo / csv data

As I am super paranoid, I also like to output all my mongo_db data into .csv files, which I then regularly backup. This will allow a system recovery, should the mongo files be corrupted.

This currently supports: FX, individual futures contract prices, multiple prices, adjusted prices.

```python
from sysproduction.update_backup_to_csv import backup_adj_to_csv

backup_adj_to_csv()
```

Linux script:
```
. $SCRIPT_PATH/update_backup_to_csv
```


# Echoes, Logging, diagnostics and reporting

We need to know what our system is doing, especially if it is fully automated. Here are the methods by which this should be done:

- Echoes of stdout output from processes that are running
- Storage of logging output in a database, tagged with keys to identify them 
- Storage of diagnostics in a database, tagged with keys to identify them 
- the option to run reports both scheduled and ad-hoc, which can optionally be automatically emailed

## Echos: stdout output

The [supplied crontab](/sysproduction/linux/crontab) contains lines like this:

```
SCRIPT_PATH="$HOME:/workspace3/psystemtrade/sysproduction/linux/scripts"
ECHO_PATH="$HOME:/echos"
#
0 6  * * 1-5 $SCRIPT_PATH/updatefxprices  >> $ECHO_PATH/updatefxprices 2>&1
```

The above line will run the script `updatefxprices`, but instead of outputting the results to stdout they will go to `updatefxprices`. These echo files are must useful when processes crash, in which case you may want to examine the stack trace. Usually however the log files will be more useful.

### Cleaning old echo files

Over time echo files can get... large (my default position for logging is verbose). To avoid this you can run [this linux script](/sysproduction/linux/scripts/truncate_echo_files) which chops them down to the last 20,000 lines (FIX ME ADD TO CRONTAB)

## Logging 

Logging in pysystemtrade is done via loggers. See the [userguide for more detail](/docs/userguide.md#logging). The logging levels are:

self.log.msg("this is a normal message")
self.log.terse("not really used in production code since everything is logged")
self.log.warn("this is a warning message means something unexpected")
self.log.error("this error message means ")
self.log.critical("this critical message will always be printed, and an email will be sent to the user. Use this if user action is required")

The default logger in production code is to the mongo database. This method will also try and email the user if a critical message is logged.

### Adding logging to your code

The default for logging is to do this via mongodb. Here is an example of logging code:

```python
from syslogdiag.log import logToMongod as logger 

def top_level_function():
    """
    This is a function that's called as the top level of a process
    """

    # can optionally pass mongodb connection attributes here
    log=logger("top-level-function")

    # note use of log.setup when passing log to other components
    conn = connectionIB(client=100, log=log.setup(component="IB-connection"))
    
    ibfxpricedata = ibFxPricesData(conn, log=log.setup(component="ibFxPricesData"))
    arcticfxdata = arcticFxPricesData(log=log.setup(component="arcticFxPricesData"))

    list_of_codes_all = ibfxpricedata.get_list_of_fxcodes()  # codes must be in .csv file /sysbrokers/IB/ibConfigSpotFx.csv
    log.msg("FX Codes: %s" % str(list_of_codes_all))
    for fx_code in list_of_codes_all:

        # Using log.label permanently adds the labelled attribute (although in this case it will be replaced on each iteration of the loop
        log.label(currency_code = fx_code)
        new_fx_prices = ibfxpricedata.get_fx_prices(fx_code) 

        if len(new_fx_prices)==0:
            log.error("Error trying to get data for %s" % fx_code)
            continue



```

The following should be used as logging attributes (failure to do so will break reporting code):

- type: the argument passed when the logger is setup. Should be the name of the top level calling function. Production types include price collection, execution and so on.
- stage: Used by stages in System objects, such as 'rawdata'
- component: other parts of the top level function that have their own loggers
- currency_code: Currency code (used for fx), format 'GBPUSD'
- instrument_code: Self explanatory
- contract_date: Self explanatory, format 'yyyymm' 
- order_id: Self explanatory, used for live trading


### Getting log data back

Python:
```python
from syslogdiag.log import accessLogFromMongodb

# can optionally pass mongodb connection attributes here
mlog = accessLogFromMongodb()
# Return a list of strings per log line
mlog.get_log_items(dict(type="top-level-function")) # any attribute directory here is fine as a filter, defaults to last days results
# Printout log entries
mlog.print_log_items(dict(type="top-level-function"), lookback_days=7) # get last weeks worth
# Return a list of logEntry objects, useful for dissecting
mlog.get_log_items_as_entries(dict(type="top-level-function"))
```


### Cleaning old logs


Python:
```python
from syslogdiag.log import accessLogFromMongodb
from sysdata.mongodb.mongo_connection import mongoDb

# can optionally pass mongodb connection attributes here
mongo_db=mongoDb()
mlog = accessLogFromMongodb(mongo_db=mongo_db)

mlog.delete_log_items_from_before_n_days(days=365) # this is also the default
```

Linux script: (defaults to last 365 days and default database
```
. $SCRIPT_PATH/truncate_log_files
```

FIX ME THIS SHOULD BE DONE EVERY DAY ONCE WE HAVE ENOUGH LOGS ADD TO CRONTAB

## Reporting

Reports are run regularly to allow you to monitor the system and decide if any action should be taken. You can choose to have them emailed to you.

Email address, server and password *must* be set in `private_config.yaml`:

```
email_address: "somebloke@anemailadress.com"
email_pwd: "h0Wm@nyLetter$ub$tiute$"
email_server: 'smtp.anemailadress.com'
```

### Roll report (Daily)

Email version:

Python:
```python
from sysproduction.email_roll_report import email_roll_report

email_roll_report()

```

Linux script:
```
. $SCRIPT_PATH/email_roll_report
```

The ad-hoc version of this report (not emailed) is:

Linux script:
```
. $SCRIPT_PATH/get_roll_info
```


# Scripts

Scripts are used to run python code which:

- runs different parts of the trading system, such as:
   - get price data
   - get FX data
   - calculate positions
   - execute trades
   - get accounting data
- runs report and diagnostics, eithier regular or ad-hoc
- Do housekeeping duties, eg truncate log files and run backups

Script are then called by [schedulers](#scheduling), or on an ad-hoc basis from the command line.

## Production system components

### Get spot FX data from interactive brokers, write to MongoDB (Daily)

Python:
```python
from sysproduction.updateFxPrices import update_fx_prices

update_fx_prices()
```

Linux script:
```
. $SCRIPT_PATH/update_fx_prices
```


This will check for 'spikes', unusually large movements in FX rates eithier when comparing new data to existing data, or within new data. If any spikes are found in data for a particular contract it will not be written. The system will attempt to email the user when a spike is detected. The user will then need to [manually check the data](#manual-check-of-fx-price-data).
.

The threshold for spikes is set in the default.yaml file, or overidden in the private config, using the paramater `max_price_spike`. Spikes are defined as a large multiple of the average absolute daily change. So for example if a price typically changes by 0.5 units a day, and `max_price_spike=6`, then a price change larger than 3 units will trigger a spike.


### Update sampled contracts (Daily)

This ensures that we are currently sampling active contracts, and updates contract expiry dates.

Python:
```python
from sysproduction.update_sampled_contracts import updated_sampled_contracts
update_sampled_prices()
```

Linux script:
```
. $SCRIPT_PATH/update_sampled_contracts
```


### Update futures contract historical price data (Daily)

This gets historical daily data from IB for all the futures contracts marked to sample in the mongoDB contracts database, and updates the Arctic futures price database.
If update sampled contracts has not yet run, it may not be getting data for all the contracts you need.

Python:
```python
from sysproduction.update_historical_prices import update_historical_prices
update_historical_prices()
```

Linux script:
```
. $SCRIPT_PATH/update_historical_prices
```

This will check for 'spikes', unusually large movements in price eithier when comparing new data to existing data, or within new data. If any spikes are found in data for a particular contract it will not be written. The system will attempt to email the user when a spike is detected. The user will then need to [manually check the data](#manual-check-of-futures-contract-historical-price-data).
.

The threshold for spikes is set in the default.yaml file, or overidden in the private config, using the paramater `max_price_spike`. Spikes are defined as a large multiple of the average absolute daily change. So for example if a price typically changes by 0.5 units a day, and `max_price_spike=6`, then a price change larger than 3 units will trigger a spike.

FIXME: An intraday sampling would be good


### Update multiple and adjusted prices (Daily)

This will update both multiple and adjusted prices with new futures per contract price data.

It should be scheduled to run once the daily prices for individual contracts have been updated.

Python:
```python
from sysproduction.update_multiple_adjusted_prices import update_multiple_adjusted_prices_daily
update_multiple_adjusted_prices_daily()
```

Linux script:
```
. $SCRIPT_PATH/update_multiple_adjusted_prices
```

Spike checks are not carried out on multiple and adjusted prices, since they should hopefully be clean if the underlying per contract prices are clean.

FIXME: An intraday sampling would be good


### Manual check of futures contract historical price data 
(Whever required)

Python:
```python
from sysproduction.update_manual_check_historical_prices import update_manual_check_historical_prices
update_manual_check_historical_prices(instrument_code)
```

Linux script:
```
. $SCRIPT_PATH/update_manual_check_historical_prices
```

The script will pull in data from interactive brokers, and the existing data, and check for spikes. If any spikes are found, then the user is interactively asked if they wish to (a) accept the spiked price, (b) use the previous time periods price instead, or (c) type a number in manually. You should check another data source to see if the spike is 'real', if so accept it, otherwise type in the correct value. Using the previous time periods value is only advisable if you are fairly sure that the price change wasn't real and you don't have a source to check with.

If a new price is typed in then that is also spike checked, to avoid fat finger errors. So you may be asked to accept a price you have have just typed in manually if that still results in a spike. Accepted or previous prices are not spike checked again.

Spikes are only checked on the FINAL price in each bar, and the user is only given the opportunity to correct the FINAL price. If the FINAL price is changed, then the OPEN, HIGH, and LOW prices are also modified; adding or subtracting the same adjustment that was made to the final price. The system does not currently use OHLC prices, but you should be aware of this creating potential inaccuracies. VOLUME figures are left unchanged if a price is corrected.

Once all spikes are checked for a given contract then the checked data is written to the database, and the system moves on to the next contract.


### Manual check of FX price data 
(Whever required)

Python:
```python
from sysproduction.update_manual_check_fx_prices import update_manual_check_fx_prices
update_manual_check_fx_prices(fx_code)
```

Linux script:
```
. $SCRIPT_PATH/uupdate_manual_check_fx_prices
```

See [manual check of futures contract prices](#manual-check-of-futures-contract-historical-price-data) for more detail. Note that as the FX data is a single series, no adjustment is required for other values.


### Roll adjusted prices 
(Whenever required)

Allows you to change the roll state and roll from one priced contract to the next.

Python:
```python
from sysproduction.update_roll_adjusted_prices import update_roll_adjusted_prices
update_roll_adjusted_prices(instrument_code)
```

Linux script:
```
. $SCRIPT_PATH/update_roll_adjusted_prices
```

### Run updated backtest systems for one or more strateges
(Usually overnight)

The paradigm for pysystemtrade is that we run a new backtest nightly, which outputs some parameters that a trading engine uses the next day. For the basic system defined in the core code those parameters are a pair of position buffers for each instrument. The trading engine will trade if the current position lies outside those buffer values.

This can easily be adapted for different kinds of trading system. So for example, for a mean reversion system the nightly backtest could output the target prices for the range. For an intraday system it could output the target position sizes and entry  / exit points. This process reduces the amount of work the trading engine has to do during the day.


Python:
```python
from sysproduction.update_run_systems import update_run_systems
run_system()
```

Linux script:
```
. $SCRIPT_PATH/update_system_example
```

See [launcher functions](#launcher-functions) for more details.



## Ad-hoc diagnostics

### Recent FX prices

Python:
```python
from sysproduction.readFxPrices import read_fx_prices
read_fx_prices("GBPUSD", tail_size=20) # print last 20 rows for cable
```

Linux command line: (arguments are asked for after script is run)
```
cd $SCRIPT_PATH
. read_fx_prices
```

### Recent futures contract prices (FIX ME TO DO)

### Recent multiple prices (FIX ME TO DO)

### Recent adjusted prices (FIX ME TO DO)

### Roll information

Get information about which markets to roll. There is also an email version of this report.

Python:
```python
from sysproduction.get_roll_info import get_roll_info
get_roll_info("EDOLLAR") ## Defaults to 'ALL'
```

Linux command line: (arguments are asked for after script is run)
```
cd $SCRIPT_PATH
. get_roll_info
```

### Examine pickled backtest state object

FIX ME TO DO

Python:
```python
```


## Housekeeping

### Delete old pickled backtest state objects

TO DO

### Clean up old log files


Python:
```python
from sysproduction.truncateLogFiles import truncate_log_files
truncate_log_files()
```

Linux command line: 
```
cd $SCRIPT_PATH
. truncate_log_files
```

### Truncate echo log files


Linux command line: 
```
cd $SCRIPT_PATH
. truncate_echo_files
```

# Scheduling

Running a fully or partially automated trading system requires the use of scheduling software that can launch new scripts at regular intervals, for example:

- processes that kick off when a machine is switched on
- processes that kick off daily 
- processes that kick off several times a day (eg regular reports or reconciliation)


## Issues to consider when constructing the schedule

Things to consider when constructing a schedule include:

- Machine load   (eg avoid running computationally intensive processes when also trading where latency could be important). This is less important if you are running multiple machines.
- Database thrashing (eg avoid running input intensive reporting processes on database tables that are being actively read / written to by more important live trading processes)
- File lock / integrity (eg avoid running backups whilst active writes are occuring)
- Robustness (eg it's probably better to have trading processes shutting down each night and then restarting in the morning, than trying to keep them running continously)


## A suggested schedule in pseudocode

Here is the schedule I use for my own trading system. Since I trade US, European, and Asian markets, I trade between midnight (9am in Asia) and 8pm (4pm in New York) local UK time. This reduces the 'dead time' when reporting and backups can take place to between 8pm and midnight.

- Midnight: If you are restarting IB Gateway on a daily basis, do it now
- Midnight: Launch processes for monitoring account value, executing trades, generating trades, and gathering intraday prices
- 6am: Get daily spot FX prices
- 6am: Run some lightweight morning reports
- 8pm: Stop processes for monitoring account value, executing trades, and gathering intraday prices
- 8pm: Clear client id tracker used by IB to avoid conflicts
- 8:30pm: Get daily 'closing' prices (some of these may not be technically closes if markets have not yet closed)
- 9:00pm: Run daily reports, and any computationally intensive processes (like running a backtest based on new prices)
- 11pm: If you are restarting IB Gateway on a daily basis, close it now.
- 11pm: Run backups
- 11pm: Truncate echo files, discard log file entries more than one year old, clear IB locked client IDs

There will be flexibility in this schedule depending on how long different processes take. Notice that I don't shut down and then launch a new interactive brokers gateway daily. Some people may prefer to do this, but I am using an authentication protocol which requires manual intervention. [This product](https://github.com/ib-controller/ib-controller/) is popular for automating the lauch of the IB gateway.

## Formal list of scheduled tasks

TO DO


## Choice of scheduling systems

You need some sort of scheduling system to kick off the various top level processes.

### Linux cron

Because I use cron myself, there are is a [cron tab included in pysystemtrade](https://github.com/robcarver17/pysystemtrade/blob/master/sysproduction/linux/crontab). 

### Windows task scheduler

I have not used this product (I don't use Windows or Mac products for ideological reasons, also they're rubbish and overpriced respectively), but in theory it should do the job.

### Python

You can use python itself as a scheduler, using something like [this](https://github.com/dbader/schedule), which gives you the advantage of being platform independent. However you will still need to ensure there is a python instance running all the time. You also need to be careful about whether you are spawning new threads or new processes, since only one connection to IB Gateway or TWS can be launched within a single process.

### Manual system

It's possible to run pysystemtrade without any scheduling, by manually starting the neccessary processes as required. This option might make sense for traders who are not running a fully automated system.

# Production system concepts

## Configuration files

### Private config

TO DO
max_price_spike
strategy_list
base_currency

### System defaults


TO DO


## Strategies

Each strategy is defined in the config parameter `strategy_list`, found eithier in the defaults.yaml file or overriden in private configuration. The following shows the parameters for an example strategy, named (appropriately enough) `example`.

```
strategy_list:
  example:
    overnight_launcher:
      function: sysproduction.system_launchers.run_system_classic.run_system_classic
      backtest_config_filename: systems.provided.futures_chapter15.futures_config.yaml
```


### Launcher functions

Launch functions run overnight backtests for each of the strategies you are running (see [here](#run-updated-backtest-systems-for-one-or-more-strateges) for more details.)

The following shows the launch function parameters for an example strategy, named (appropriately enough) `example`.

```
strategy_list:
  example:
    overnight_launcher:
      function: sysproduction.system_launchers.run_system_classic.run_system_classic
      backtest_config_filename: systems.provided.futures_chapter15.futures_config.yaml
```

The configuration for the overnight launcher includes the launcher function; the other configuration values are passed as keyword arguments to the launcher function.
Launcher functions must include the strategy name and a data 'blob' as their first two arguments. 

A launcher usually does the following:

- get the amount of capital currently in your trading account. This is set by  FIX ME CAPITAL MODULE TO BE WRITTEN
- run a backtest using that amount of capital
- get the position buffer limits, and save these down (for the classic system, other systems may save different values down)
- store the backtest state (pickled cache) in the directory specified by the parameter csv_backup_directory (set in your private config file, or the system defaults file), subdirectory strategy name, filename date and time generated. It also copies the config file used to generate this backtest with a similar naming pattern.

As an example here is the provided 'classic' launcher function:

```python
def run_system_classic(strategy_name, data,
               backtest_config_filename="systems.provided.futures_chapter15.futures_config.yaml",
               ):


        capital_value = get_capital(data, strategy_name)

        system = production_classic_futures_system(backtest_config_filename,
                                            log=data.log, notional_trading_capital=capital_value,
                                           )

        updated_buffered_positions(data, strategy_name, system)

        store_backtest_state(data, system, strategy_name=strategy_name,
                             backtest_config_filename=backtest_config_filename)
        return success
```


# Production system data and data flow


TO DO


# Production system classes

## Data blobs and the classes that feed on them

TO DO


## Reporting and diagnostics

TO DO

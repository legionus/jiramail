# jiramail

The `jiramail` is mail transport for Atlassian's Jira service written in Go. This utility
stores data (`projects`, `sprints`, `issues`, `comments`, etc.) from jira to local maildir.
Optionally for making changes, it provides an SMTP interface.

# Runtime

There are two ways to run the utility. The first and the main way when the utility
in an infinite loop after a some period of time synchronizes the state. The second way, when
the utility is started once, synchronizes the state and finishes execution:

```bash
jiramail -1
```

# Folders layout

The utility will create the following directory hierarchy:

```
{Destdir}
  ⤷ {RemoteName}
    ⤷ boards
      ⤷ {BoardName}
        ⤷ backlog
        ⤷ epics
          ⤷ {EpicName}
        ⤷ sprints
          ⤷ {SprintName}
    ⤷ projects
      ⤷ {ProjectKey}
```

Known problem: If the name of the `board`, `epic` or `sprint` changes, a new maildir will be created.
If I use identifiers, it becomes very uninformative.

# Configuration

Example:

```yaml
core:
  loglevel: debug
  logfile: ~/logs/jiramail.log
  lockdir: ~/tmp/jiramail.lock
smtp:
  addr: 127.0.0.1:10025
  lockdir: ~/tmp/jirasmtp.lock
  auth:
    username: jiramail
    password: SMTP-PRIVATE-KEY
remote:
  coreos:
    destdir: ~/Mail/jira/coreos
    baseurl: https://jira.coreos.com
    username: legionus
    password: PRIVATE
    projectmatch: DEVEXP
    boardmatch: DEVEXEP
    delete: remove
```

# Mail client

You can use any mail client that can read the local mailbox in the `maildir` format.

# SMTP server

The utility provides a special SMTP server so that you can make changes in the Jira. It does not
send emails anywhere, but only performs API requests based on them. So this is not a real SMTP server.

The server understands the context and the necessary parameters when you reply to the generated message.
So it matters to which message you reply.

If you reply to the message and send it to:

### To: reply@jira

* reply to `issue` will add new comment, but if you use `reply+subtask@jira` then a subtask will be created;
* reply to `comment` will add new comment;
* reply to `project` will create a new issue.

### To: edit@jira

The reply to this address is used to edit the `Subject` and the body of the message. Be careful and do not
forget about quoting in your mail client. This operation is valid for `issues` and `comments`.

To update only subject of issue, use the address: `edit+subject@jira`. Same with the body of the message.
To update only the body, use the address: `edit+body@jira`.

### To: bot@jira

This is a special address where the body of the message is treated as a sequence of directives.
Each directive should take one line. Arguments with spaces must be specified in quota (as in shell).
Lines starting with '#' or '>' will be ignored.
This operation is valid for `issues`

#### Change labels

```
jira labels add "label one" "label two"
jira labels remove no-qe
```

#### Change state

```
jira state "in progress"
jira state To Do
```
Argument is not case sensitive.

#### Change priority

```
jira priority high
jira priority low
```
Argument is not case sensitive.

#### Assignee

```
jira assignee to me
jira assignee to legionus
```

#### Watchers

```
jira watchers add user1
jira watchers remove user2
```

#### Story points

Atlassian's Jira does not have a standard field for story points, so you need to have a custom
field with name `Story points` and type either a number or a string.

```
jira story points 5
```

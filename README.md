# jiramail

 The `jiramail` is mail transport for Atlassian's Jira service. This utility
 stores data into mailbox.

My main desire is to use mutt to read jira tickets.

## Configuration

The utility uses a config file to store authentication information.

```toml
[jira]
server = "https://issues.redhat.com/"
auth = "token"
token = "<sometoken>"
```

## Usage

The utility can both read the state of jira and make changes.

### Sub-Command: jiramail mbox
To fetch the full change history of the ticket with all comments as emails:

```
jiramail.sh mbox --query "project = RHEL" rhel.mbox
jiramail.sh mbox --issue RHEL-123 single.mbox
jiramail.sh mbox --assignee "user" user.mbox
```

The command will create a mailbox if it does not exist or add emails to an
existing one.

### Sub-Command: jiramail change

This subcommand reads commands from to make changes to jira. Commands can be in
letters in mailbox or sent to stdin.

#### Assign Ticket

```
jira issue <ISSUE-123> assign <user>
jira issue <ISSUE-123> assign %me
```
where `<ISSUE-123>` is the issue identifier in jira and `<user>` is username.
The special value `%me` is used to assign a ticket to yourself.

#### Add Comment

```
jira issue <ISSUE-123> comment "Some useful text"
jira issue <ISSUE-123> comment <<EOF
Some
multi-line
comment.
EOF
```
You can use shell-like heredoc if you need to specify a multi-line comment.

#### Change Fields

```
jira issue <ISSUE-123> change <field1> set <value1>
jira issue <ISSUE-123> change <field2> add <value2>
```
A `<field>` can be specified by name or by id. If there are spaces in the field
name, you can use quotes. For example `fixVersions` or `"Fix Version/s"`.

If field is an array then it is possible to add an element. To do this, use the
`add` operator. If you need to overwrite all values, then use `set`.

You can combine multiple changes into one command:
```
jira issue <ISSUE-123> change \
    <field1> set <value1> \
    <field2> set <value2> \
    <field3> set <value3>
```

## License

jiramail is licensed under the GNU General Public License (GPL), version 3.


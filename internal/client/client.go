package client

import (
	"fmt"
	"net/http"

	"github.com/andygrunwald/go-jira"
	"github.com/sirupsen/logrus"

	"github.com/legionus/jiramail/internal/config"
	"github.com/legionus/jiramail/internal/jiraplus"
)

func NewClient(c *config.Configuration, remoteName string) (*jiraplus.Client, error) {
	r, ok := c.Remote[remoteName]
	if !ok {
		return nil, fmt.Errorf("remote is not defined in the configuration")
	}

	var httpClient *http.Client

	if len(r.Username) > 0 {
		trans := jira.BasicAuthTransport{
			Username: r.Username,
			Password: r.Password,
		}
		httpClient = trans.Client()
	}

	jiraClient, err := jira.NewClient(httpClient, r.BaseURL)
	if err != nil {
		return nil, fmt.Errorf("unable to create client: %s", err)
	}

	user, resp, err := jiraClient.User.GetSelf()
	if err != nil {
		if resp.StatusCode == 401 {
			return nil, fmt.Errorf("authentication credentials are incorrect or missing")
		}
		return nil, fmt.Errorf("unable to create client: %s", err)
	}

	logrus.Debugf("remote %q, use the user %q to synchronize", remoteName, user.Key)

	return jiraplus.NewClient(jiraClient), nil
}

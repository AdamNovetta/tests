<?php
// -----------------------------------------------------------------------------
// Authentication function to get return on if user (PHP_AUTH_USER logged in)
// is a member of the group passed to the function. This is useful for checking
// http/https apache auth'ed users are part of a group (or not) for IAM on pages
// you might want to secure.
//
// Returns a True/False for the user being in the group
// (need to fill in ####VARIABLES#### per LDAP server settings)
// Aleclerc@novetta.com - 2016
// -----------------------------------------------------------------------------

function ldap_authorized($group) {
if (!isset($_SERVER['PHP_AUTH_USER'])) {
    header("WWW-Authenticate: Basic realm=\"Private Area\"");
    header("HTTP/1.0 401 Unauthorized");
    // only reached if authentication fails
    print "Sorry - you need to login to access this page... please reload and try again\n";
    exit;
}
else {
    // only reached if basic HTTPS authentication succeeds
$ldaphost = '####LDAP SERVER####';
$ldapport = 636;
$ds = ldap_connect($ldaphost, $ldapport)
or die("Could not connect to $ldaphost");
    ldap_set_option($ds, LDAP_OPT_PROTOCOL_VERSION, 3);
    ldap_set_option($ds, LDAP_OPT_REFERRALS, 0);
    //ldap_set_option($ds, LDAP_OPT_DEBUG_LEVEL, 7);
if ($ds)
{
    $bind_username = "####BIND USER FULL DN####";
    $bind_passwd = "####BIND PW####";
    $ldapbind = ldap_bind($ds, $bind_username, $bind_passwd);
    $ldaptree = "####OU/DN FOR USERS####";
    $ldap_user = $_SERVER['PHP_AUTH_USER'];
    // Debug stuff user/group selection
    //$ldap_user = "adamtest";
    $filter="(member=*$ldap_user*)";
    $onlythis = array("member");
    // $ds is a valid link identifier for a directory server

    if ($ldapbind)
        {
          //print "Congratulations! $username is authenticated.";
          $result = ldap_search($ds, $ldaptree, $filter, $onlythis);
          $data = ldap_get_entries($ds, $result);
          $needle = "uid=$ldap_user,####LDAP CONTEXT####";
          $flipped_haystack = array_flip($data['0']['member']);
          if ( isset($flipped_haystack[$needle]))
          {
            return true;
          }
          else {
            return false;
          }
          // Debug ldap stuff
          //echo '<h3>date dump</h3><pre>';
          //print_r($data);
          //print_r($flipped_haystack);
          //echo '</pre>';
          // /end debug ldap stuff
        }
    else
        {
            return false;
        }
      }
    }
  }
?>
